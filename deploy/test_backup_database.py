from contextlib import closing
import sqlite3
import tarfile
import tempfile
import unittest
from pathlib import Path

from backup_database import backup


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

    def test_missing_inputs_do_not_create_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                backup(root / 'missing.db', root / 'assets', root / 'backups')
            self.assertFalse((root / 'backups').exists())


if __name__ == '__main__':
    unittest.main()
