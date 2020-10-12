from time import sleep
from .common import terminate_through_http
from subprocess import Popen
from pathlib import Path

stdout_write = print


def get_mtimes(files) -> dict:
    mtimes = {}
    for p in files:
        try:
            mtimes[p] = p.stat().st_mtime
        except FileNotFoundError:
            pass
    return mtimes


def main(remaining_argv):
    if not remaining_argv:
        remaining_argv = ['8000']
    port = remaining_argv[0]

    proc = Popen(['otree', 'devserver_inner'] + remaining_argv)
    root = Path('.')

    files_to_watch = [p for p in root.glob('**/*.py') if 'migrations' not in str(p)]

    mtimes = get_mtimes(files_to_watch)
    while True:
        exit_code = proc.poll()
        if exit_code is not None:
            return exit_code
        new_mtimes = get_mtimes(files_to_watch)
        changed_file = None
        for f in files_to_watch:
            if f in new_mtimes and f in mtimes and new_mtimes[f] != mtimes[f]:
                changed_file = f
                break
        if changed_file:
            stdout_write(changed_file, 'changed, restarting')
            mtimes = new_mtimes
            try:
                terminate_through_http(port)
            # handling it here instead of inside the function since it may
            # not affect zipserver (need to investigate)
            except ConnectionResetError:
                pass
            proc.wait()
            proc = Popen(['otree', 'devserver_inner', port, '--is-reload'])
        sleep(1)
