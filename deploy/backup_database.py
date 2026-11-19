#!/usr/bin/env python3
"""Create a private, consistent SQLite snapshot and archive migrated assets."""
import argparse
from contextlib import closing
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tarfile
import tempfile
import uuid


def backup(database, assets, destination):
    database, assets, destination = map(Path, (database, assets, destination))
    if not database.is_file():
        raise FileNotFoundError(f'Database not found: {database}')
    if not assets.is_dir():
        raise FileNotFoundError(f'Asset directory not found: {assets}')
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    final = destination / f'backup-{stamp}-{uuid.uuid4().hex[:8]}'
    temporary = Path(tempfile.mkdtemp(prefix='.backup-', dir=destination))
    try:
        # URI read-only mode prevents accidentally creating an empty source database.
        with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(temporary / 'database.db')) as snapshot:
                source.backup(snapshot)
                if snapshot.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise RuntimeError('Database integrity check failed')
        with tarfile.open(temporary / 'assets.tar.gz', 'w:gz') as archive:
            archive.add(assets, arcname='assets')
        os.rename(temporary, final)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return final


def upload_backup(directory, client, bucket):
    """Upload both files, then publish a manifest only after verification."""
    directory = Path(directory)
    prefix = f'backups/{directory.name}'
    files = {}
    for name in ('database.db', 'assets.tar.gz'):
        path = directory / name
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(chunk)
        checksum = digest.hexdigest()
        key = f'{prefix}/{name}'
        client.upload_file(str(path), bucket, key,
                           ExtraArgs={'Metadata': {'sha256': checksum}})
        remote = client.head_object(Bucket=bucket, Key=key)
        if remote['ContentLength'] != path.stat().st_size or remote.get('Metadata', {}).get('sha256') != checksum:
            raise RuntimeError(f'Upload verification failed: {key}')
        files[name] = {'size': path.stat().st_size, 'sha256': checksum}
    client.put_object(Bucket=bucket, Key=f'{prefix}/manifest.json',
                      Body=json.dumps({'files': files}, sort_keys=True).encode('utf-8'),
                      ContentType='application/json')
    return prefix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='/opt/bearblog/data/dev.db')
    parser.add_argument('--assets', default='/opt/bearblog/content/assets')
    parser.add_argument('--destination', default='/opt/bearblog/backups')
    parser.add_argument('--upload-r2', action='store_true')
    args = parser.parse_args()
    result = backup(args.database, args.assets, args.destination)
    print(f'Local backup: {result}', flush=True)
    if args.upload_r2:
        import boto3
        access_key = os.environ.get('BACKUP_R2_ACCESS_KEY_ID')
        secret_key = os.environ.get('BACKUP_R2_SECRET_ACCESS_KEY')
        if not access_key or not secret_key:
            raise RuntimeError('BACKUP_R2_ACCESS_KEY_ID and BACKUP_R2_SECRET_ACCESS_KEY are required')
        client = boto3.client('s3', endpoint_url='https://0e016704dc5552d28010732c3d050a64.r2.cloudflarestorage.com',
                              region_name='auto', aws_access_key_id=access_key,
                              aws_secret_access_key=secret_key)
        prefix = upload_backup(result, client, 'blog-backup')
        print(f'R2 backup: blog-backup/{prefix}', flush=True)


if __name__ == '__main__':
    main()
