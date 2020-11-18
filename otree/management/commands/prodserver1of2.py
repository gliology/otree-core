import asyncio
import logging
import os
from otree.common import dump_db
from django.core.management.base import BaseCommand
import uvicorn
from uvicorn.main import Config, ChangeReload, Multiprocess, Server
import sys
from otree_startup.asgi import application

logger = logging.getLogger(__name__)


class OTreeUvicornServer(Server):
    def __init__(self, config, *, is_devserver):
        self.is_devserver = is_devserver
        super().__init__(config)

    def handle_exit(self, sig, frame):
        if self.is_devserver:
            dump_db()
        return super().handle_exit(sig, frame)


def run_asgi_server(addr, port, *, is_devserver=False):

    '''modified uvicorn.main.run to use our custom subclasses'''

    config = Config(
        'otree_startup.asgi:application',
        host=addr,
        port=int(port),
        log_level='warning' if is_devserver else "info",
        # i suspect it was defaulting to something else
        workers=1,
        # this loads the DB in a subprocess.
        # reload=is_devserver,
    )
    server = OTreeUvicornServer(config=config, is_devserver=is_devserver)

    assert config.workers == 1
    if config.should_reload:
        sock = config.bind_socket()
        supervisor = ChangeReload(config, target=server.run, sockets=[sock])
        supervisor.run()
    else:
        server.run()


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
        run_asgi_server(addr, port)
