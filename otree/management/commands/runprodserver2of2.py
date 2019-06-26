#!/usr/bin/env python
import os
import sys
from sys import exit as sys_exit

from honcho.manager import Manager as HonchoManager
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run timeoutworker and botworker.'

    def add_arguments(self, parser):
        BaseCommand.add_arguments(self, parser)

    def handle(self, *args, verbosity=1, **options):
        # TODO: what is this for?
        self.verbosity = verbosity
        manager = self.get_honcho_manager()
        manager.loop()
        sys_exit(manager.returncode)

    def get_honcho_manager(self):

        env_copy = os.environ.copy()

        manager = HonchoManager()

        # if I change these, I need to modify the ServerCheck also
        manager.add_process(
            'botworker',
            'otree botworker',
            quiet=False,
            env=env_copy,
        )
        manager.add_process(
            'timeoutworkeronly',
            'otree timeoutworkeronly',
            quiet=False,
            env=env_copy,
        )

        return manager

