"""Pull deploy's current content into this checkout without creating Git commits.

Run: python -I scripts/sync_personal_content.py
Only content files are transferred. Tokens, users and SQLite are never fetched.
"""
import argparse
import base64
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parent.parent / 'content'
RECEIPT = ROOT / '.content-sync.json'


def ssh(host, command):
    result = subprocess.run(['tailscale', 'ssh', host, command], capture_output=True, timeout=600)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace'))
    return result.stdout


def remote_python(code):
    return 'python3 -I -c ' + shlex.quote(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def valid_name(name):
    p = PurePosixPath(name)
    return (not p.is_absolute() and all(x not in ('..', '.') for x in p.parts)
            and '\\' not in name and ':' not in name and str(p) == name
            and (name in ('blog.json', 'manifest.json') or name.startswith(('posts/', 'assets/'))))


@contextlib.contextmanager
def sync_lock():
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / '.content-sync.lock').open('a+b') as handle:
        try:
            if os.name == 'nt':
                import msvcrt
                handle.seek(0)
                if not handle.read(1):
                    handle.write(b'0')
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('Another content sync is already running') from exc
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def synchronize():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='root@deploy')
    parser.add_argument('--deployment', default='/opt/bearblog')
    parser.add_argument('--accept-server', action='store_true', help='Explicitly replace conflicting local content files')
    args = parser.parse_args()
    deployment = args.deployment.rstrip('/')
    # Export first, then capture a hash inventory while holding the export lock.
    inventory_code = f'''
import sys, json, hashlib
sys.path.insert(0, '/app')
import django
django.setup()
from blogs.content_store import _lock, export_content
from pathlib import Path
root = Path('/app/content')
export_content(root)
with _lock(root):
    files = [root/'blog.json', root/'manifest.json']
    files += [root/'posts'/name for name in json.loads((root/'manifest.json').read_text())]
    files += [p for p in (root/'assets').rglob('*') if p.is_file()]
    result = {{str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    print(json.dumps(result))
'''
    command = 'cd ' + shlex.quote(deployment) + ' && docker compose exec -T bearblog python -c ' + shlex.quote(inventory_code)
    inventory = json.loads(ssh(args.host, command))
    if not isinstance(inventory, dict) or any(not valid_name(name) for name in inventory):
        raise ValueError('Invalid server file inventory')
    previous = json.loads(RECEIPT.read_text(encoding='utf-8')) if RECEIPT.exists() else {}
    changed, conflicts, local_states = [], [], {}
    for name, expected in inventory.items():
        target = ROOT.joinpath(*PurePosixPath(name).parts)
        current = digest(target.read_bytes()) if target.exists() else None
        local_states[name] = current
        if current == expected:
            continue
        if ((name in previous and current != previous[name]) or
                (name not in previous and current is not None)) and not args.accept_server:
            conflicts.append(name)
        changed.append(name)
    deleted = [name for name in previous if name not in inventory]
    for name in deleted:
        if not valid_name(name):
            raise ValueError('Invalid previous inventory')
        target = ROOT / name
        current = digest(target.read_bytes()) if target.exists() else None
        local_states[name] = current
        if current is not None and current != previous[name] and not args.accept_server:
            conflicts.append(name)
    if conflicts:
        raise ValueError('Local edits conflict with server; preserve or commit them before using --accept-server: ' + ', '.join(conflicts))
    payload = {}
    if changed:
        # Only changed files cross Tailscale. Hash checks detect edits racing the download.
        fetch_code = f'''
import io, tarfile, base64
from pathlib import Path
root=Path({(deployment + '/content')!r})
buf=io.BytesIO()
with tarfile.open(fileobj=buf, mode='w:gz') as archive:
    for name in {changed!r}:
        archive.add(root/name, arcname=name, recursive=False)
print(base64.b64encode(buf.getvalue()).decode('ascii'))
'''
        data = base64.b64decode(ssh(args.host, remote_python(fetch_code)), validate=False)
        # Do not extract an untrusted tar archive to the filesystem.
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            for member in archive.getmembers():
                if not member.isfile() or member.name not in changed or member.name in payload:
                    raise ValueError('Unexpected archive member')
                body = archive.extractfile(member).read()
                if digest(body) != inventory[member.name]:
                    raise ValueError('Server content changed during sync; run again')
                payload[member.name] = body
        if set(payload) != set(changed):
            raise ValueError('Incomplete server archive')
    # Recheck immediately before publishing; an editor may have saved while
    # the network transfer was running. Even --accept-server must not race it.
    for name, initial in local_states.items():
        target = ROOT / name
        current = digest(target.read_bytes()) if target.exists() else None
        if current != initial:
            raise ValueError('Local content changed during sync; run again: ' + name)
    # All data has been verified before changing local files.
    ROOT.mkdir(parents=True, exist_ok=True)
    for name, body in payload.items():
        target = ROOT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name('.content-' + target.name)
        temporary.write_bytes(body)
        temporary.replace(target)
    for name in deleted:
        (ROOT / name).unlink(missing_ok=True)
    receipt_tmp = RECEIPT.with_name('.content-sync-receipt.tmp')
    receipt_tmp.write_text(json.dumps(inventory, indent=2) + '\n', encoding='utf-8')
    receipt_tmp.replace(RECEIPT)
    print(f'Content verified: {len(inventory)} files; updated {len(changed)}, removed {len(deleted)}. No Git commit created.')


if __name__ == '__main__':
    try:
        with sync_lock():
            synchronize()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        sys.exit(str(exc))
