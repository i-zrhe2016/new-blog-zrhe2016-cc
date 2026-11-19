from contextlib import closing
import sqlite3
import tarfile
import tempfile
import unittest
from unittest.mock import MagicMock
import json
from pathlib import Path

from backup_database import backup, upload_backup


class BackupTests(unittest.TestCase):
    def test_snapshot_includes_wal_and_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / 'content' / 'assets'
            assets.mkdir(parents=True)
            (assets / 'image.svg').write_text('image', encoding='utf-8')
            with closing(sqlite3.connect(root / 'live.db')) as db:
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('CREATE TABLE posts (body TEXT)')
                db.execute('INSERT INTO posts VALUES (?)', ('draft',))
                db.commit()
                result = backup(root / 'live.db', assets, root / 'backups')
                with closing(sqlite3.connect(result / 'database.db')) as restored:
                    self.assertEqual(restored.execute('SELECT body FROM posts').fetchone(), ('draft',))
                with tarfile.open(result / 'assets.tar.gz') as archive:
                    self.assertEqual(archive.extractfile('assets/image.svg').read(), b'image')

    def test_upload_publishes_manifest_only_after_both_objects_verify(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'backup-test'
            root.mkdir()
            (root / 'database.db').write_bytes(b'database')
            (root / 'assets.tar.gz').write_bytes(b'assets')
            client = MagicMock()
            uploaded = {}

            def upload(path, bucket, key, ExtraArgs):
                uploaded[key] = (Path(path).stat().st_size, ExtraArgs['Metadata'])

            def head(Bucket, Key):
                size, metadata = uploaded[Key]
                return {'ContentLength': size, 'Metadata': metadata}

            client.upload_file.side_effect = upload
            client.head_object.side_effect = head
            self.assertEqual(upload_backup(root, client, 'blog-backup'), 'backups/backup-test')
            manifest = json.loads(client.put_object.call_args.kwargs['Body'])
            self.assertEqual(set(manifest['files']), {'database.db', 'assets.tar.gz'})
            client.put_object.reset_mock()
            client.head_object.return_value = {'ContentLength': 0}
            client.head_object.side_effect = None
            with self.assertRaises(RuntimeError):
                upload_backup(root, client, 'blog-backup')
            client.put_object.assert_not_called()

    def test_missing_inputs_do_not_create_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                backup(root / 'missing.db', root / 'assets', root / 'backups')
            self.assertFalse((root / 'backups').exists())


if __name__ == '__main__':
    unittest.main()
