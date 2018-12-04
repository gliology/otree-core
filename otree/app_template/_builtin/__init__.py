# Don't change anything in this file.
from ..models import Subsession, Group, Player
import otree.api


class Page(otree.api.Page):
    subsession: Subsession
    group: Group
    player: Player


class WaitPage(otree.api.WaitPage):
    subsession: Subsession
    group: Group


class Bot(otree.api.Bot):
    subsession: Subsession
    group: Group
    player: Player
