import tarfile
import logging
import os.path
import sys
from pathlib import Path
import contextlib
from tempfile import TemporaryDirectory
from otree.management.commands.unzip import unzip
import os.path
import os, time
import subprocess
import shutil

logger = logging.getLogger(__name__)


def main(remaining_argv):
    '''
    - top-level process that keeps checking for new files
    - subprocess that actually runs the server
    '''
    try:
        if remaining_argv:
            exit_code = run_single_zipfile(remaining_argv[0])
        else:
            exit_code = autoreload_for_new_zipfiles()
        # if child process crashes, we should kill this process also
        if exit_code < 0:
            os.kill(os.getpid(), -exit_code)
        else:
            sys.exit(exit_code)
    except KeyboardInterrupt:
        pass

def run_single_zipfile(fn: str):
    tempdir = unzip_to_tempdir(fn)
    unzip(fn, tempdir.name)
    proc = run_devserver(tempdir)
    return proc.wait()


def autoreload_for_new_zipfiles() -> int:
    current_zipfile = get_newest_zipfile()
    current_time = get_time(current_zipfile)
    tempdirs = []
    try:
        while True:
            tempdir = unzip_to_tempdir(current_zipfile.name)
            if tempdirs:
                # get __temp_migrations and sqlite DB from previous one
                previous_tempdir = Path(tempdirs[-1].name)
                for item in ['__temp_migrations', 'db.sqlite3']:
                    item_path = previous_tempdir / item
                    if item_path.exists():
                        shutil.move(str(item_path), tempdir.name)

            tempdirs.append(tempdir)

            proc = run_devserver(tempdir)

            while True:
                # if process is still running, poll() returns None
                exit_code = proc.poll()
                if exit_code != None:
                    return exit_code
                time.sleep(1)
                current_zipfile = get_newest_zipfile()
                updated_time = get_time(current_zipfile)
                if updated_time > current_time:
                    current_time = updated_time
                    # use stdout.write because logger is not configured
                    # (django setup has not even been run)
                    sys.stdout.write(f'new project found: {current_zipfile}\n')
                    proc.terminate()
                    break
    finally:
        for td in tempdirs:
            td.cleanup()




def get_time(path: Path):
    return path.stat().st_mtime


def run_devserver(tempdir: TemporaryDirectory) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, 'manage.py', 'devserver', '--noreload'],
        cwd=tempdir.name,
        env=os.environ.copy(),
    )


def unzip_to_tempdir(zipfile: str) -> TemporaryDirectory:
    tempdir = TemporaryDirectory()
    unzip(zipfile, tempdir.name)
    return tempdir



def get_newest_zipfile() -> Path:
    user_dir = Path('.')
    zipfiles = sorted(user_dir.glob('*.otreezip'), key=get_time, reverse=True)
    if not zipfiles:
        sys.stdout.write('No *.otreezip file found in this folder')
        sys.exit(-1)

    newest_zipfile = zipfiles[0]

    # cleanup so they don't end up with hundreds of zipfiles
    for zf in zipfiles[10:]:
        sys.stdout.write('deleting old file', zf.name)
        zf.unlink()

    return newest_zipfile

