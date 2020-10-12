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
    try:
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
                terminate_through_http(port)
                proc.wait()
                proc = Popen(['otree', 'devserver_inner', port, '--is-reload'])
            sleep(1)
    except KeyboardInterrupt:
        # handle KeyboardInterrupt so we don't get a traceback to console
        # also, we wait a couple seconds for the subprocess to exit.
        # The KeyboardInterrupt automatically terminates the subprocess,
        # but it seems the subprocess can take longer to exit than this process,
        # resulting in errant console output
        proc.wait(2)
