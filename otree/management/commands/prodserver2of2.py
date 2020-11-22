# run the worker to enforce page timeouts
# even if the user closes their browser
import redis.exceptions
import os
import sys
from django.core.management import BaseCommand, CommandError
from otree.tasks import Worker, get_redis_client


class Command(BaseCommand):
    def handle(self, *args, **options):
        if not os.environ.get('REDIS_URL'):
            sys.exit(
                'Error: ensure that Redis is installed and that REDIS_URL env var is defined.'
            )

        try:
            conn = get_redis_client()
        except redis.exceptions.ConnectionError as exc:
            sys.exit(f'Could not connect to Redis: {exc}')

        Worker(conn).redis_listen()
