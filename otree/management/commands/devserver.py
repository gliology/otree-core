import importlib
import os
import os.path
import pathlib
import sys
import termcolor
import time
import traceback
from django.conf import settings
from django.core.management import call_command
from django.db.migrations import exceptions as migrations_excs
from django.db.utils import OperationalError
from pathlib import Path

from otree.common_internal import capture_stdout

from . import runserver

TMP_MIGRATIONS_DIR = '__temp_migrations'

ADVICE_DELETE_TMP = (
    "ADVICE: Try deleting the folder {}. If that doesn't work, "
    "look for the error in your models.py."
).format(TMP_MIGRATIONS_DIR)

ADVICE_PRINT_DETAILS = (
    '(For technical details about this error, run "otree devserver --details")'
)

is_sqlite = settings.DATABASES['default']['ENGINE'].endswith('sqlite3')
if is_sqlite:
    ADVICE_DELETE_DB = (
        'ADVICE: Try deleting the file db.sqlite3 in your project folder.'
    )
else:
    ADVICE_DELETE_DB = 'ADVICE: Try deleting your database.'

ADVICE_DELETE_DB += (
    ' Then run "otree devserver", not "otree resetdb".'
)


class Command(runserver.Command):

    show_error_details = False

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--details', action='store_true', dest='show_error_details', default=False,
            help="Show details if an error occurs")

    def inner_run(self, *args, **options):

        self.show_error_details = options['show_error_details']
        self.handle_migrations()

        super().inner_run(*args, **options)

    def handle_migrations(self):

        migrate_apps = settings.INSTALLED_OTREE_APPS + ['otree']
        # it used to be
        # but i don't see any reason not to just to INSTALLED_APPS
        migrations_modules = {
            app_name: '{}.{}'.format(TMP_MIGRATIONS_DIR, app_name)
            for app_name in migrate_apps
        }

        settings.MIGRATION_MODULES = migrations_modules

        migrations_dir_path = os.path.join(settings.BASE_DIR, TMP_MIGRATIONS_DIR)
        pathlib.Path(TMP_MIGRATIONS_DIR).mkdir(exist_ok=True)

        init_file_path = os.path.join(migrations_dir_path, '__init__.py')
        pathlib.Path(init_file_path).touch(exist_ok=True)

        self.perf_check()

        start = time.time()

        try:
            # makemigrations rarely sends any interesting info to stdout.
            # if there is an error, it will go to stdout,
            # or raise CommandError.
            # if someone needs to see the details of makemigrations,
            # they can do "otree makemigrations".
            with capture_stdout():
                call_command('makemigrations', '--noinput', *migrations_modules.keys())
        except Exception:
            self.print_error_and_exit(ADVICE_DELETE_TMP)

        # migrate imports some modules that were created on the fly,
        # so according to the docs for import_module, we need to call
        # invalidate_cache.
        # the following line is necessary to avoid a crash I experienced
        # on Mac, because makemigrations tries some imports which cause ImportErrors,
        # messes up the cache on some systems.
        importlib.invalidate_caches()

        try:
            # see above comment about makemigrations and capture_stdout.
            # it applies to migrate command also.
            with capture_stdout():
                # call_command does not add much overhead (0.1 seconds typical)
                call_command('migrate', '--noinput')
        except (OperationalError, migrations_excs.InconsistentMigrationHistory):
            self.print_error_and_exit(ADVICE_DELETE_DB)

        total_time = round(time.time() - start, 1)
        if total_time > 5:
            self.stdout.write('makemigrations & migrate ran in {}s'.format(total_time))

    def print_error_and_exit(self, advice):
        self.stdout.write('\n')
        if self.show_error_details:
            traceback.print_exc()
        else:
            self.stdout.write('An error occurred.')
        termcolor.cprint(advice, 'white', 'on_red')
        if not self.show_error_details:
            self.stdout.write(ADVICE_PRINT_DETAILS)
        sys.exit(0)

    def perf_check(self):
        '''after about 150 migrations,
        load time increased from 0.6 to 1.2+ second'''

        MAX_MIGRATIONS = 200

        # we want to delete migrations files, but keep __init__.py
        # and directories, because then we don't need to
        # migrations files are named 0001_xxx.py, 0002_xxx.py, etc.
        # so, we assume they will all
        file_glob = '{}/*/0*.py'.format(TMP_MIGRATIONS_DIR)
        python_fns = list(Path('.').glob(file_glob))
        num_files = len(python_fns)

        if num_files > MAX_MIGRATIONS:
            advice = (
                'You have too many migrations files ({}). '
                'This can slow down performance. '
                'You should delete the directory {} '
                'and also delete your database.'
            ).format(num_files, TMP_MIGRATIONS_DIR)
            termcolor.cprint(advice, 'white', 'on_red')
