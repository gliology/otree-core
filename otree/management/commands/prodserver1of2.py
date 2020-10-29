import asyncio
import logging
import os

from django.core.management.base import BaseCommand
from hypercorn.asyncio import serve
from hypercorn.config import Config

from otree_startup.asgi import application

logger = logging.getLogger(__name__)

# when I put the shutdown_event in common.py, I get this error on py 3.8 (not 3.7):
# RuntimeError: Task <Task pending name='Task-5' coro=<raise_shutdown() running at ...\hypercorn\utils.py:172>>
# got Future <Future pending> attached to a different loop
shutdown_event = asyncio.Event()


def run_hypercorn(addr, port, *, is_devserver=False):

    config = Config()
    config.bind = f'{addr}:{port}'
    if is_devserver:
        # We want to hide "Running on 127.0.0.1 over https (CTRL + C to quit)")
        # and show our localhost message instead.
        # hypercorn doesn't seem to log anything important to .info anyway.
        config.loglevel = 'warning'
    else:
        config.accesslog = '-'  # go to stdout
        # for some reason access_log_format works with hypercorn 0.9.2 but not 0.11
        config.access_log_format = '%(h)s %(S)s "%(r)s" %(s)s'

    loop = asyncio.get_event_loop()

    # shutdown_event is used so that it terminates gracefully
    # when i was doing sys.exit() in the TerminateServer view,
    # it kept printing out the SystemExit traceback but not actually terminating the server
    loop.run_until_complete(
        serve(application, config, shutdown_trigger=shutdown_event.wait,)
    )


def get_addr_port(cli_addrport, is_devserver=False):
    default_addr = '127.0.0.1' if is_devserver else '0.0.0.0'
    default_port = os.environ.get('PORT') or 8000
    if not cli_addrport:
        return default_addr, default_port
    parts = cli_addrport.split(':')
    if len(parts) == 1:
        return default_addr, parts[0]
    return parts


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'addrport', nargs='?', help='Optional port number, or ipaddr:port'
        )

    def handle(self, *args, addrport=None, verbosity=1, **kwargs):
        addr, port = get_addr_port(addrport)
        run_hypercorn(addr, port)
