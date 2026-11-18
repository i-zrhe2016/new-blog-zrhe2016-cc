import base64
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('content_sync', Path(__file__).with_name('sync_personal_content.py'))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SyncTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.receipt = self.root / '.content-sync.json'
        patches = [patch.object(sync, 'ROOT', self.root), patch.object(sync, 'RECEIPT', self.receipt), patch.object(sys, 'argv', ['sync'])]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def inventory(self, body):
        return {'blog.json': sync.digest(body)}

    def archive(self, body):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode='w:gz') as t:
            info = tarfile.TarInfo('blog.json')
            info.size = len(body)
            t.addfile(info, io.BytesIO(body))
        return base64.b64encode(buf.getvalue())

    def test_preserves_local_deletion(self):
        self.receipt.write_text(json.dumps(self.inventory(b'old')))
        with patch.object(sync, 'ssh', return_value=json.dumps(self.inventory(b'new')).encode()):
            with self.assertRaisesRegex(ValueError, 'Local edits conflict'):
                sync.synchronize()
        self.assertFalse((self.root / 'blog.json').exists())

    def test_preserves_edits_during_download(self):
        target = self.root / 'blog.json'
        target.write_bytes(b'old')
        self.receipt.write_text(json.dumps(self.inventory(b'old')))
        calls = 0
        def remote(*args):
            nonlocal calls
            calls += 1
            if calls == 1:
                return json.dumps(self.inventory(b'new')).encode()
            target.write_bytes(b'editing')
            return self.archive(b'new')
        with patch.object(sync, 'ssh', side_effect=remote):
            with self.assertRaisesRegex(ValueError, 'changed during sync'):
                sync.synchronize()
        self.assertEqual(target.read_bytes(), b'editing')

    def test_rejects_corrupt_download(self):
        replies = [json.dumps(self.inventory(b'new')).encode(), self.archive(b'corrupt')]
        with patch.object(sync, 'ssh', side_effect=replies):
            with self.assertRaisesRegex(ValueError, 'Server content changed'):
                sync.synchronize()
        self.assertFalse((self.root / 'blog.json').exists())

    def test_sync_is_repeatable_and_locked(self):
        replies = [json.dumps(self.inventory(b'new')).encode(), self.archive(b'new')]
        with sync.sync_lock():
            with self.assertRaisesRegex(RuntimeError, 'already running'):
                with sync.sync_lock():
                    pass
            with patch.object(sync, 'ssh', side_effect=replies):
                sync.synchronize()
        with patch.object(sync, 'ssh', return_value=replies[0]) as remote:
            sync.synchronize()
            self.assertEqual(remote.call_count, 1)
        self.assertEqual((self.root / 'blog.json').read_bytes(), b'new')


if __name__ == '__main__':
    unittest.main()
