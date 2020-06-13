import os
from sys import exit as sys_exit

import honcho.manager
from django.core.management.base import BaseCommand

# made this simple class to reduce code duplication,
# and to make testing easier (I didn't know how to check that it was called
# with os.environ.copy(), especially if we patch os.environ)
class OTreeHonchoManager(honcho.manager.Manager):
    def add_otree_process(self, name, cmd):
        self.add_process(name, cmd, env=os.environ.copy(), quiet=False)


class Command(BaseCommand):
    def handle(self, *args, verbosity=1, **options):
        # TODO: what is this for?
        self.verbosity = verbosity
        manager = self.get_honcho_manager()
        manager.loop()
        sys_exit(manager.returncode)

    def get_honcho_manager(self):
        manager = OTreeHonchoManager()
        manager.add_otree_process('worker', 'otree prodserver2of2_worker')
        manager.add_otree_process('huey', 'otree prodserver2of2_huey')
        return manager
