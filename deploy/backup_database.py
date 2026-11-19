#!/usr/bin/env python3
"""Create a private, consistent SQLite snapshot and archive migrated assets."""
import argparse
from contextlib import closing
import datetime
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='/opt/bearblog/data/dev.db')
    parser.add_argument('--assets', default='/opt/bearblog/content/assets')
    parser.add_argument('--destination', default='/opt/bearblog/backups')
    args = parser.parse_args()
    print(backup(args.database, args.assets, args.destination))


if __name__ == '__main__':
    main()
