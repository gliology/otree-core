from django.core.management.base import BaseCommand
import tarfile
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)

BASE_DIR = settings.BASE_DIR

# don't want to use the .gitignore format, it looks like a mini-language
# https://git-scm.com/docs/gitignore#_pattern_format

# TODO: maybe some of these extensions like .env, staticfiles could legitimately exist in subfolders.
EXCLUDED_PATH_ENDINGS = '~ .git db.sqlite3 .pyo .pyc .pyd .idea venv _static_root staticfiles __pycache__ .env'.split()

# always use the same name for simplicity and so that we don't get bloat
# or even worse, all the previous zips being included in this one
# call it zipped.tar so that it shows up alphabetically last
# (using __temp prefix makes it show up in the middle, because it's a file)
ARCHIVE_NAME = 'zipped.tgz'

# TODO: make sure we recognize and exclude virtualenvs, even if not called venv

def filter_func(tar_info: tarfile.TarInfo):

    path = tar_info.path


    for ending in EXCLUDED_PATH_ENDINGS:
        if path.endswith(ending):
            return None

    if '__temp' in path:
        return None

    # size is in bytes
    kb = tar_info.size >> 10
    if kb > 500:
        logger.info(f'Adding large file ({kb} KB): {path}')

    #print(path)
    return tar_info


class Command(BaseCommand):
    help = ("Zip into an archive")

    def handle(self, **options):
        # w:gz
        with tarfile.open(ARCHIVE_NAME, 'w:gz') as tar:
            tar.add(BASE_DIR, arcname='proj', filter=filter_func)
        logger.info(f'Saved your code into file "{ARCHIVE_NAME}"')
