import os
import logging
from django.core.management import call_command
from . import prodserver2of2

logger = logging.getLogger(__name__)


class Command(prodserver2of2.Command):
    addrport: str

    def add_arguments(self, parser):
        parser.add_argument(
            'addrport', nargs='?', help='Optional port number, or ipaddr:port'
        )
        parser.add_argument(
            '--no-collectstatic',
            action='store_false',
            dest='collectstatic',
            default=True,
        )

    def handle(self, *args, addrport=None, collectstatic, **options):
        self.addrport = addrport
        if collectstatic:
            self.stdout.write('Running collectstatic ...')
            call_command('collectstatic', interactive=False, verbosity=1)

        return super().handle(*args, **options)

    def get_honcho_manager(self):
        manager = super().get_honcho_manager()
        cmd = ['otree', 'prodserver1of2']
        if self.addrport:
            cmd.append(self.addrport)
        manager.add_otree_process('asgiserver', cmd)

        return manager
