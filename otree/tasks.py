import random
import heapq
import json
from logging import getLogger
from time import time, sleep
from urllib import request, parse
from urllib.error import URLError
from urllib.parse import urljoin

import otree.constants
from django.conf import settings

print_function = print

in_memory_base_url = ''

logger = getLogger(__name__)
TIMEOUTWORKER_REDIS_KEY = 'otree-timeoutworker'


def post(url, data: dict):
    '''
    make the request over the network rather than in-process,
    to avoid race conditions. everything must be handled by the main
    server instance.
    '''
    data = parse.urlencode(data).encode()
    req = request.Request(url, data=data)  # this will make the method "POST"
    resp = request.urlopen(req)


def get(url):
    try:
        request.urlopen(url)
    # some users were reporting URLError but not clear what URL it was
    except URLError as exc:
        raise Exception(f'Error occurred when opening {url}: {repr(exc)}') from None


def enqueue(queue, method, kwargs, delay):
    # random.random() is the tiebreaker, so we don't resort to comparing kwargs
    heapq.heappush(queue, (time() + delay, random.random(), method, kwargs))


class Worker:
    def __init__(self, redis_conn):
        self.redis_conn = redis_conn
        # flush old stuff
        redis_conn.delete(TIMEOUTWORKER_REDIS_KEY)

    def redis_listen(self):
        print_function('timeoutworker is listening for messages through Redis')
        q = []
        while True:
            result = self.redis_conn.blpop(TIMEOUTWORKER_REDIS_KEY, timeout=3)
            if result:
                _, message_bytes = result
                message = json.loads(message_bytes.decode('utf-8'))
                enqueue(q, **message)
            while q and q[0][0] < time():
                _, _, method, kwargs = heapq.heappop(q)
                try:
                    getattr(self, method)(**kwargs)
                except Exception as exc:
                    # don't raise, because then this would crash.
                    # logger.exception() will record the full traceback
                    logger.exception(repr(exc))

    def submit_expired_url(self, participant_code, base_url, path):
        if 'testserver' in base_url:
            base_url = in_memory_base_url
            if not base_url:
                return

        from otree.models.participant import Participant

        # if the participant exists in the DB,
        # and they did not advance past the page yet

        # To reduce redundant server traffic, it's OK not to advance the page if the user already got to the next page
        # themselves, or via "advance slowest participants".
        # however, we must make sure that the user succeeded in loading the next page fully.
        # if the user made this page's POST but closed their browser before
        # the redirect to the next page's GET, then if the next page has a timeout,
        # it will not get scheduled, and then the auto-timeout chain would be broken.
        # so, instead of filtering by _index_in_pages (which is set in POST),
        # we filter by _current_form_page_url (which is set in GET,
        # AFTER the next page's timeout is scheduled.)

        if Participant.objects.filter(
            code=participant_code, _current_form_page_url=path
        ).exists():
            post(urljoin(base_url, path), data={otree.constants.timeout_happened: True})

    def ensure_pages_visited(self, base_url, participant_pks):
        """This is necessary when a wait page is followed by a timeout page.
        We can't guarantee the user's browser will properly continue to poll
        the wait page and get redirected, so after a grace period we load the page
        automatically, to kick off the expiration timer of the timeout page.
        """

        if 'testserver' in base_url:
            base_url = in_memory_base_url
            if not base_url:
                return

        from otree.models.participant import Participant

        # we used to filter by _index_in_pages, but that is not reliable,
        # because of the race condition described above.
        unvisited_participants = Participant.objects.filter(pk__in=participant_pks)
        for participant in unvisited_participants:

            # if the wait page is the first page,
            # then _current_form_page_url could be null.
            # in this case, use the start_url() instead,
            # because that will redirect to the current wait page.
            # (alternatively we could define _current_page_url or
            # current_wait_page_url)
            get(urljoin(base_url, participant._url_i_should_be_on()))

    def set_base_url(self, url):
        '''this is necessary because advance_last_place_participants uses the test client, which has a bogus url of
        http://testserver that doesn't work when we make requests over the network.
        '''
        global in_memory_base_url
        in_memory_base_url = url


_main_process_redis = None


def get_redis_client():
    '''
    (1) redis is an expensive import
    (2) we can't instantiate redis globally because REDIS_URL may not be defined'''
    global _main_process_redis
    if _main_process_redis is None:
        from redis import StrictRedis

        _main_process_redis = StrictRedis.from_url(settings.REDIS_URL)
    return _main_process_redis


def redis_enqueue(method, delay, kwargs):
    get_redis_client().rpush(
        TIMEOUTWORKER_REDIS_KEY,
        json.dumps(dict(method=method, delay=delay, kwargs=kwargs)),
    )


def set_base_url(url):
    redis_enqueue(method='ensure_pages_visited', delay=0, kwargs=dict(url=url))


def ensure_pages_visited(delay, **kwargs):
    redis_enqueue(method='ensure_pages_visited', delay=delay, kwargs=kwargs)


def submit_expired_url(delay, **kwargs):
    redis_enqueue(method='submit_expired_url', delay=delay, kwargs=kwargs)
