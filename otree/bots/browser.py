import json
import logging
import random
import threading
import traceback
from collections import OrderedDict
from typing import Dict, Tuple

import otree.db.idmap
import otree.common
from otree import common
from otree.common import get_redis_conn, get_models_module
from otree.models import Session, Participant
from otree.models_concrete import ParticipantToPlayerLookup
from .bot import ParticipantBot
from .runner import make_bots
import otree.channels.utils as channel_utils


REDIS_KEY_PREFIX = 'otree-bots'

# if you are testing all configs from the CLI browser bot launcher,
# and each app has multiple cases, it's possible to end up with many
# bots in the history.
# usually this wouldn't matter,
# but timeoutworker may try to load the pages after they have been completed
# (it will POST then get redirected to GET)
SESSIONS_PRUNE_LIMIT = 80

# global variable that holds the browser bot worker instance in memory
browser_bot_worker = None  # type: BotAndLiveWorker

# these locks are only necessary when using runserver
# because then the botworker stuff is done by one of the 4 worker threads.
prepare_submit_lock = threading.Lock()
add_or_remove_bot_lock = threading.Lock()

logger = logging.getLogger('otree.test.browser_bots')


class BadRequestError(Exception):
    '''
    if USE_REDIS==True, this exception will be converted to a dict
    and passed through Redis.
    if USE_REDIS==False, this will raise normally.
    '''

    pass


PARTICIPANT_NOT_IN_BOTWORKER_MSG = (
    "Participant {participant_code} not loaded in botworker. "
    "This can happen for several reasons: "
    "(1) You are running multiple botworkers "
    "(2) You restarted the botworker after creating the session "
    "(3) The bots expired "
    "(the botworker stores bots for "
    "only the most recent {prune_limit} sessions)."
)


class BaseWorker:
    redis_conn = None

    def ping(self, *args, **kwargs):
        pass

    def redis_listen(self):
        print('botworker is listening for messages through Redis')
        while True:
            self.try_process_one_redis_message()

    def try_process_one_redis_message(self):
        '''break it out into a separate method for testing purposes'''

        # blpop returns a tuple
        result = None

        # put it in a loop so that we can still receive KeyboardInterrupts
        # otherwise it will block
        while result is None:
            result = self.redis_conn.blpop(REDIS_KEY_PREFIX, timeout=3)

        key, message_bytes = result
        message = json.loads(message_bytes.decode('utf-8'))
        response_key = message['response_key']
        kwargs = message['kwargs']
        method = getattr(self, message['method'])

        try:
            retval = method(**kwargs)
            response = {'retval': retval}
        except BadRequestError as exc:
            # request error means the request received through Redis
            # was invalid.
            # use str instead of repr here
            response = {'error': str(exc)}
        except Exception as exc:
            # un-anticipated error
            response = {'error': repr(exc), 'traceback': traceback.format_exc()}
            # don't raise, because then this would crash.
            # logger.exception() will record the full traceback
            logger.exception(repr(exc))
        finally:
            retval_json = json.dumps(response)
            self.redis_conn.rpush(response_key, retval_json)


class BotAndLiveWorker(BaseWorker):
    def __init__(self, redis_conn=None):
        self.redis_conn = redis_conn
        self.participants_by_session = OrderedDict()
        self.browser_bots: Dict[str, ParticipantBot] = {}
        self.queued_post_data: Dict[str, Dict] = {}

    def initialize_session(self, session_pk, case_number):
        self.prune()
        self.participants_by_session[session_pk] = []

        session = Session.objects.get(pk=session_pk)
        if case_number is None:
            # choose one randomly
            from otree.session import SessionConfig

            config = SessionConfig(session.config)
            num_cases = config.get_num_bot_cases()
            case_number = random.choice(range(num_cases))

        bots = make_bots(
            session_pk=session_pk, case_number=case_number, use_browser_bots=True
        )
        for bot in bots:
            self.participants_by_session[session_pk].append(bot.participant_code)
            self.browser_bots[bot.participant_code] = bot

    def prune(self):
        '''to avoid memory leaks'''
        with add_or_remove_bot_lock:
            if len(self.participants_by_session) > SESSIONS_PRUNE_LIMIT:
                _, p_codes = self.participants_by_session.popitem(last=False)
                for participant_code in p_codes:
                    self.browser_bots.pop(participant_code, None)

    def get_bot(self, participant_code):
        try:
            return self.browser_bots[participant_code]
        except KeyError:
            msg = PARTICIPANT_NOT_IN_BOTWORKER_MSG.format(
                participant_code=participant_code, prune_limit=SESSIONS_PRUNE_LIMIT
            )
            raise BadRequestError(msg)

    def enqueue_next_post_data(self, participant_code) -> bool:
        bot = self.get_bot(participant_code)
        try:
            self.queued_post_data[participant_code] = next(bot.submits_generator)
        except StopIteration:
            # don't prune it because can cause flakiness if
            # there are other GET requests coming in. it will be pruned
            # when new sessions are created anyway.

            # return None instead of raising an exception, because
            # None can easily be serialized in Redis. Means the code can be
            # basically the same for Redis and non-Redis
            return False
        else:
            return True

    def pop_enqueued_post_data(self, participant_code) -> Dict:
        # because we are returning it through Redis, need to pop it
        # here
        submission = self.queued_post_data[participant_code]
        # 2020-03-16: why do we remove page_class when we are only going to use post_data anyway?
        submission.pop('page_class')
        return submission['post_data']

    def set_attributes(self, participant_code, request_path, html):
        bot = self.get_bot(participant_code)
        # so that any asserts in the PlayerBot work.
        bot.path = request_path
        bot.html = html

    def send_live_payload(self, participant_code, page_name, payload):
        participant = Participant.objects.get(code=participant_code)
        # we have to verify the ParticipantToPlayerLookup,
        # to know that the user is currently on that page.
        player_lookup = ParticipantToPlayerLookup.objects.get(
            participant=participant, page_index=participant._index_in_pages
        )
        app_name = player_lookup.app_name
        models_module = otree.common.get_models_module(app_name)
        pages_module = otree.common.get_pages_module(app_name)
        assert f'/{page_name}/' in player_lookup.url
        PageClass = getattr(pages_module, page_name)
        method_name = PageClass.live_method

        with otree.db.idmap.use_cache():
            player = models_module.Player.objects.get(id=player_lookup.player_pk)
            group = player.group
            method = getattr(group, method_name)
            retval = method(player.id_in_group, payload)
            otree.db.idmap.save_objects()

        if not retval:
            return
        if not isinstance(retval, dict):
            msg = f'{method_name} must return a dict'
            raise Exception(msg)
        players = group.get_players()
        pcodes_dict = {p.id_in_group: p.participant.code for p in players}

        if 0 not in retval:
            for pid in retval:
                if pid not in pcodes_dict:
                    msg = f'{method_name} has invalid return value. No player with id_in_group={repr(pid)}'
                    raise Exception(msg)

        group_name = channel_utils.live_group(
            participant.session.code, player_lookup.page_index
        )

        pcode_retval = {}
        for pid, pcode in pcodes_dict.items():
            payload = retval.get(pid) or retval.get(0)
            if payload is not None:
                pcode_retval[pcode] = payload

        channel_utils.sync_group_send_wrapper(
            group=group_name, type='send_back_to_client', event=pcode_retval
        )


class BotWorkerPingError(Exception):
    pass


def ping(redis_conn, *, timeout):
    '''
    timeout arg is required because this is often called together
    with another function that has a timeout. need to be aware of double
    timeouts piling up.
    '''
    response_key = redis_enqueue_method_call(
        redis_conn=redis_conn, method_name='ping', method_kwargs={}
    )

    # make it very long, so we don't get spurious ping errors
    result = redis_conn.blpop(response_key, timeout)

    if result is None:
        msg = (
            'If you want to use browser bots or live pages, '
            'you need to start the worker process. '
            'If using Heroku, you must turn on the second dyno.'
        )
        raise BotWorkerPingError(msg)


def load_redis_response_dict(response_bytes: bytes):
    response = json.loads(response_bytes.decode('utf-8'))
    # response_error only exists if using Redis.
    # if using runserver, there is no need for this because the
    # exception is raised in the same thread.
    if 'traceback' in response:
        # cram the other traceback in this traceback message.
        # note:
        raise common.BotError(response['traceback'])
    elif 'error' in response:
        # handled exception
        raise BadRequestError(response['error'])
    return response['retval']


def redis_flush_bots(redis_conn):
    for key in redis_conn.scan_iter(match='{}*'.format(REDIS_KEY_PREFIX)):
        redis_conn.delete(key)


def redis_enqueue_method_call(redis_conn, method_name, method_kwargs) -> str:
    response_key = '{}-{}'.format(REDIS_KEY_PREFIX, random.randint(1, 10 ** 9))
    msg = {'method': method_name, 'kwargs': method_kwargs, 'response_key': response_key}
    redis_conn.rpush(REDIS_KEY_PREFIX, json.dumps(msg))
    return response_key


def redis_get_method_retval(redis_conn, response_key: str) -> dict:
    '''
    returns return value (if any) or raises an exception
    this is separate from redis_push for easier testing
    '''

    # timeout:
    # in practice is very fast...around 1ms
    # however, if an exception occurs, could take quite long.
    # so, make this very long so we don't get spurious errors.
    # no advantage to cutting it off early.
    # if it's that slow consistently, people will complain.
    result = redis_conn.blpop(response_key, timeout=6)
    if result is None:
        # ping will raise if it times out
        ping(redis_conn, timeout=3)
        raise Exception('botworker is running but did not return a submission.')
    key, submit_bytes = result
    return load_redis_response_dict(submit_bytes)


def wrap_method_call(method_name: str, method_kwargs):
    if otree.common.USE_REDIS:
        redis_conn = get_redis_conn()
        response_key = redis_enqueue_method_call(
            redis_conn=redis_conn, method_name=method_name, method_kwargs=method_kwargs
        )
        return redis_get_method_retval(redis_conn=redis_conn, response_key=response_key)
    else:
        method = getattr(browser_bot_worker, method_name)
        return method(**method_kwargs)


def set_attributes(**kwargs):
    return wrap_method_call('set_attributes', kwargs)


def enqueue_next_post_data(**kwargs) -> dict:
    return wrap_method_call('enqueue_next_post_data', kwargs)


def pop_enqueued_post_data(**kwargs) -> dict:
    return wrap_method_call('pop_enqueued_post_data', kwargs)


def send_live_payload(**kwargs):
    wrap_method_call('send_live_payload', kwargs)


def initialize_session(**kwargs):
    # FIXME: need a timeout?
    # timeout must be int.
    # my tests show that it can initialize about 3000 players per second.
    # so 300-500 is conservative, plus pad for a few seconds
    # timeout = int(6 + num_players_total / 500)
    # maybe number of ParticipantToPlayerLookups?

    timeout = 6  # FIXME: adjust to number of players
    return wrap_method_call('initialize_session', kwargs)


def send_completion_message(*, session_code, participant_code):
    group_name = channel_utils.browser_bots_launcher_group(session_code)

    channel_utils.sync_group_send_wrapper(
        group=group_name,
        type='send_completion_message',
        event={'text': participant_code},
    )
