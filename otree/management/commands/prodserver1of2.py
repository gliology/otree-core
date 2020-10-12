import os
import re
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
import otree
import hypercorn.run
from hypercorn.config import Config

import asyncio
from hypercorn.asyncio import serve
from otree_startup.asgi import application
from otree.common import shutdown_event


naiveip_re = re.compile(
    r"""^(?:
(?P<addr>
    (?P<ipv4>\d{1,3}(?:\.\d{1,3}){3}) |         # IPv4 address
    (?P<ipv6>\[[a-fA-F0-9:]+\]) |               # IPv6 address
    (?P<fqdn>[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*) # FQDN
):)?(?P<port>\d+)$""",
    re.X,
)

logger = logging.getLogger(__name__)

DEFAULT_PORT = "8000"
DEFAULT_ADDR = '0.0.0.0'


def run_hypercorn(addr, port, *, log_each_request=False):
    config = dict(binds=f'{addr}:{port}')
    if log_each_request:
        config.update(
            accesslog='-', access_log_format='%(h)s %(S)s "%(r)s" %(s)s',
        )
    loop = asyncio.get_event_loop()

    loop.run_until_complete(
        serve(
            application,
            Config.from_mapping(config),
            shutdown_trigger=shutdown_event.wait,
        )
    )


def get_addr_port(cli_addrport):
    if cli_addrport:
        m = re.match(naiveip_re, cli_addrport)
        if m is None:
            msg = (
                '"%s" is not a valid port number '
                'or address:port pair.' % cli_addrport
            )
            raise CommandError(msg)
        addr, _, _, _, port = m.groups()
    else:
        addr = None
        port = None

    addr = addr or DEFAULT_ADDR
    # Heroku uses PORT env var
    port = port or os.environ.get('PORT') or DEFAULT_PORT
    return addr, port


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'addrport', nargs='?', help='Optional port number, or ipaddr:port'
        )

    def handle(self, *args, addrport=None, verbosity=1, **kwargs):
        addr, port = get_addr_port(addrport)
        run_hypercorn(addr, port, log_each_request=True)
