from . import runserver
from django.core.management import call_command
from django.conf import settings
import time
import pathlib
import os.path
from django.db.utils import OperationalError
from django.db.migrations import exceptions as migrations_excs
import sys
import traceback
from colorama import Fore
import importlib

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

class Command(runserver.Command):

    def inner_run(self, *args, **options):

        self.handle_migrations()

        super().inner_run(*args, **options)

    def handle_migrations(self):

        migrations_modules = {
            app_name: '{}.{}'.format(TMP_MIGRATIONS_DIR, app_name)
            for app_name in settings.INSTALLED_OTREE_APPS + ['otree']
        }

        settings.MIGRATION_MODULES = migrations_modules

        migrations_dir_path = os.path.join(settings.BASE_DIR, TMP_MIGRATIONS_DIR)
        pathlib.Path(TMP_MIGRATIONS_DIR).mkdir(exist_ok=True)

        init_file_path = os.path.join(migrations_dir_path, '__init__.py')
        pathlib.Path(init_file_path).touch(exist_ok=True)

        start = time.time()

        try:
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
            call_command('migrate', '--noinput')
        except (OperationalError, migrations_excs.InconsistentMigrationHistory):
            self.print_error_and_exit(ADVICE_DELETE_DB)

        total_time = round(time.time() - start, 1)
        if total_time > 5:
            self.stdout.write('makemigrations & migrate ran in {}s'.format(total_time))

    def print_error_and_exit(self, advice):
        self.stdout.write('\n')
        traceback.print_exc()
        self.stdout.write(Fore.RED + advice)
        sys.exit()
