import otree.common
from otree.channels import utils as channel_utils
from otree.models import Participant
from otree.lookup import get_page_lookup
import logging
from otree.database import NoResultFound

logger = logging.getLogger(__name__)


async def trial_payload_function(participant_code, page_name, msg):

    # print('in trial_payload_function', msg)
    try:
        participant = Participant.objects_get(code=participant_code)
    except NoResultFound:
        logger.warning(f'Participant not found: {participant_code}')
        return

    def send_error():
        """need to put it in a function, otherwise we get a warning
        that the coroutine wasn't awaited."""
        return _send_back(
            participant_code,
            participant._index_in_pages,
            dict(type='error'),
        )

    lookup = get_page_lookup(participant._session_code, participant._index_in_pages)
    app_name = lookup.app_name
    models_module = otree.common.get_models_module(app_name)
    PageClass = lookup.page_class
    if page_name != PageClass.__name__:
        logger.warning(
            f'Ignoring message from {participant_code} because '
            f'they are on page {PageClass.__name__}, not {page_name}.'
        )
        await send_error()

    player = models_module.Player.objects_get(
        round_number=lookup.round_number, participant=participant
    )
    Trial = PageClass.trial_model
    trial = get_current_trial(Trial, player)
    msg_type = msg['type']
    is_page_load = msg_type == 'load'
    resp = dict(is_page_load=is_page_load, type=msg_type)
    if trial and msg_type == 'response':
        if trial.id != msg['trial_id']:
            await send_error()
            msg = (
                "Trials: server and client are out of sync. "
                "Check if there were any errors earlier."
            )
            raise Exception(msg)
        response: dict = msg['response']
        if hasattr(PageClass, 'evaluate_trial'):
            try:
                feedback = PageClass.evaluate_trial(trial, response)
            except Exception:
                await send_error()
                raise
        else:
            server_fields = set(PageClass.trial_response_fields)
            client_fields = response.keys()
            server_only = server_fields - client_fields
            if server_only:
                await send_error()
                msg = (
                    "The following fields are in trial_response_fields, "
                    f"but were not sent from sendTrialResponse: {server_only}"
                )
                raise Exception(msg)
            client_only = client_fields - server_fields
            if client_only:
                await send_error()
                msg = (
                    "The following fields were sent from the sendTrialResponse, "
                    f"but are not in trial_response_fields: {client_only}"
                )
                raise Exception(msg)
            try:
                # need to do it this way rather than having an overridable evaluate_trial,
                # because it's a static method, so has no access to trial_response_fields.
                for attr in PageClass.trial_response_fields:
                    setattr(trial, attr, response[attr])
            except Exception:
                await send_error()
                raise
            trial.queue_position = None
            feedback = {}
        resp.update(feedback=feedback)
        trial = get_current_trial(Trial, player)
    if trial:
        resp.update(trial=encode_trial(trial, PageClass.trial_stimulus_fields))
    else:
        resp.update(trial=None)
    resp.update(progress=get_progress(Trial, player))
    # print('resp', resp)
    await _send_back(
        participant.code,
        participant._index_in_pages,
        resp,
    )


def encode_trial(trial, fields):
    if 'id' not in fields:
        fields.append('id')
    return {attr: getattr(trial, attr) for attr in fields}


def get_progress(Trial, player) -> dict:
    trials = Trial.objects_filter(player=player)
    total = trials.count()
    remaining = trials.filter(Trial.queue_position != None).count()

    return dict(total=total, remaining=remaining, completed=total - remaining)


def get_current_trial(Trial, player):
    return (
        Trial.objects_filter(Trial.queue_position != None, player=player)
        .order_by('queue_position')
        .first()
    )


async def _send_back(pcode, page_index, resp):
    '''separate function for easier patching'''

    group_name = channel_utils.trial_group(pcode, page_index)
    await channel_utils.group_send(
        group=group_name,
        data=resp,
    )
