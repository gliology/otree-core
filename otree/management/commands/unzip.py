from django.core.management.base import BaseCommand
import tarfile
import logging
import os.path
import sys

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Unzip a zipped oTree project"

    def add_arguments(self, parser):
        parser.add_argument(
            'zip_file', type=str, help="The .otreezip file")
        # it's good to require this arg because then it's obvious that the files
        # will be put in that subfolder, and not dumped in the current dir
        parser.add_argument(
            'output_folder', type=str,
            help="What to call the new project folder")

    def handle(self, **options):
        if os.path.isfile('settings.py') and os.path.isfile('manage.py'):
            self.stdout.write(
                'You are trying to create a project but it seems you are '
                'already in a project folder (found settings.py and manage.py).'
            )
            sys.exit(-1)

        zip_file = options['zip_file']
        output_folder = options['output_folder']

        with tarfile.open(zip_file) as tar:
            tar.extractall(output_folder)
        logger.info(f'Unzipped code into folder "{output_folder}"')
        logger.info(
            "Run 'pip3 install -r requirements.txt' to install this project's dependencies."
        )

    def run_from_argv(self, argv):
        '''
        override this because the built-in django one executes system checks,
        which trips because settings are not configured.
        as at 2018-11-19, 'unzip' is the only
        otree-specific management command that doesn't require settings
        '''

        parser = self.create_parser(argv[0], argv[1])
        options = parser.parse_args(argv[2:])
        cmd_options = vars(options)
        self.handle(**cmd_options)
