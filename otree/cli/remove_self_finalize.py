import shutil
from collections import namedtuple
from pathlib import Path

from otree import settings
from .base import BaseCommand

print_function = print

MethodInfo = namedtuple('MethodInfo', ['start', 'stop', 'name', 'model'])


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput', action='store_false', dest='interactive', default=True,
        )

    def handle(self, *args, **options):
        for app in settings.OTREE_APPS:
            remove_old_format(app)


def remove_old_format(app_name):
    approot = Path(app_name)
    app_path = approot / 'app.py'
    if not app_path.exists():
        return
    pages_path = approot / 'pages.py'
    models_path = approot / 'models.py'
    if pages_path.exists():
        pages_path.unlink()
    if models_path.exists():
        models_path.unlink()
    _builtin = approot.joinpath('_builtin')
    if _builtin.exists():
        shutil.rmtree(_builtin)
    templates = approot.joinpath('templates', app_name)
    if templates.exists():
        shutil.copytree(templates, approot, dirs_exist_ok=True)
        shutil.rmtree(approot.joinpath('templates'))
    tests_noself = approot.joinpath('tests_noself.py')
    tests_path = approot.joinpath('tests.py')
    if tests_noself.exists():
        tests_path.unlink(missing_ok=True)
        tests_noself.rename(tests_path)
