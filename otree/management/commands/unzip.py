from django.core.management.base import BaseCommand, CommandError
import tarfile
import logging
import os.path
import sys
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Unzip a zipped oTree project"

    def add_arguments(self, parser):
        parser.add_argument(
            'zip_file', type=str, help="The .otreezip file")
        # it's good to require this arg because then it's obvious that the files
        # will be put in that subfolder, and not dumped in the current dir
        parser.add_argument(
            'output_folder', type=str, nargs='?',
            help="What to call the new project folder")

    def auto_named_output_folder(self, zip_file_name):
        base_folder_name = Path(zip_file_name).stem

        for x in range(1, 50):
            if x == 1:
                folder_name = base_folder_name
            else:
                folder_name = f'{base_folder_name}-{x}'
            if not Path(folder_name).exists():
                return folder_name
        logger.error(
            f"Could not unzip the file; target folder {folder_name} already exists. "
        )
        sys.exit(-1)

    def handle(self, **options):
        if os.path.isfile('settings.py') and os.path.isfile('manage.py'):
            self.stdout.write(
                'You are trying to create a project but it seems you are '
                'already in a project folder (found settings.py and manage.py).'
            )
            sys.exit(-1)

        zip_file = options['zip_file']
        output_folder = options['output_folder']

        if not output_folder:
            output_folder = self.auto_named_output_folder(zip_file)

        with tarfile.open(zip_file) as tar:
            tar.extractall(output_folder)
        msg = (
            f'Unzipped code into folder "{output_folder}"\n'
            'Enter "cd {}" to move inside the project folder,\n'
            "then run 'pip3 install -r requirements.txt' to install this project's dependencies."
        ).format(output_folder)

        logger.info(msg)

    def run_from_argv(self, argv):
        '''
        override this because the built-in django one executes system checks,
        which trips because settings are not configured.
        as at 2018-11-19, 'unzip' is the only
        otree-specific management command that doesn't require settings
        '''

        parser = self.create_parser(argv[0], argv[1])

        try:
            options = parser.parse_args(argv[2:])
        except CommandError:
            self.stdout.write(
                'You must provide the name of the *.otreezip file. Example:\n '
                'otree unzip AAA.otreezip'
            )
            sys.exit(-1)
        cmd_options = vars(options)
        self.handle(**cmd_options)
