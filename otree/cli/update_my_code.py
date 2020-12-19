import re
import sys
from pathlib import Path
import otree
from .base import BaseCommand
from itertools import chain

item_index = 1

NEW_MODELS_PY_IMPORTS = """
from otree.api import (
    models,
    widgets,
    BaseConstants,
    BaseSubsession,
    BaseGroup,
    BasePlayer,
    Currency as c,
    currency_range,
)
"""

NEW_PAGES_PY_IMPORTS = """
from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import Constants
"""


print_function = print


def print_numbered(txt):
    global item_index
    print_function(f'\t{item_index}. {txt}')
    item_index += 1


class Command(BaseCommand):
    something_changed = False

    def handle(self, *args, **options):

        root = Path('.')

        # old format imported otree.test and otree.views, so we need to get rid of it
        _builtins = root.glob('*/_builtin/__init__.py')
        for pth in _builtins:
            if 'z_autocomplete' in pth.read_text():
                new_text = (
                    Path(otree.__file__)
                    .parent.joinpath('app_template/_builtin/__init__.py')
                    .read_text()
                )
                pth.write_text(new_text)

        settings_py = Path('settings.py').read_text('utf8')
        for substring in [
            'import otree.settings',
            'otree.settings.augment_settings(globals())',
            'from boto.mturk import qualification',
            'import dj_database_url',
        ]:
            if substring in settings_py:
                print_numbered(
                    f'Your settings.py contains "{substring}". You should delete this line.'
                )

        if 'DATABASES = {' in settings_py:
            print_numbered(
                'settings.py contains a DATABASES setting. you should delete it.'
            )

        for pth in root.glob('*/models.py'):
            txt = pth.read_text('utf8')
            if 'widgets.Slider' in txt:
                print_numbered(
                    f'{pth} uses widgets.Slider. This widget has been removed from oTree. '
                    'You should instead remove this widget and use an <input type="range"> in the template (see the docs).'
                )
            if 'widgets.CheckboxInput' in txt:
                print_numbered(
                    f'{pth} uses widgets.CheckboxInput. This widget has been removed from oTree. '
                    'You should instead remove this widget and use an <input type="checkbox"> in the template (see the docs).'
                )
            if 'models.DecimalField' in txt:
                print_numbered(
                    f'{pth} uses models.DecimalField. You should use models.FloatField instead. '
                )
            if 'subsession = models.ForeignKey(Subsession)' in txt:
                print_numbered(
                    f'{pth} uses models.ForeignKey. You should delete all foreign keys. '
                )

            substrings = [
                'from otree.common',
                'from otree.constants',
                'from otree.models',
                'from otree.db',
            ]

            if any(substring in txt for substring in substrings):
                print_numbered(
                    f'{pth} imports non-API modules from otree. '
                    f'You should change the lines at the top to:\n{NEW_MODELS_PY_IMPORTS}'
                )

        for views_py in root.glob('*/views.py'):
            pages_py = views_py.parent.joinpath('pages.py')
            if not pages_py.exists():
                views_py.rename(pages_py)
                print_function('AUTOMATIC: renamed views.py to pages.py')

        base_html = Path('_templates/global/Base.html')
        page_html = Path('_templates/global/Page.html')
        if base_html.exists() and not page_html.exists():
            base_html.rename(page_html)
            print_function('AUTOMATIC: renamed global/Base.html to global/Page.html')

        for pth in root.glob('*/pages.py'):
            txt = pth.read_text('utf8')

            if 'form_model = models.Player' in txt:
                print_numbered(
                    f"""In {pth}, you should change:\nform_model = models.Player\nto:\nform_model = 'player'"""
                )
            if 'form_model = models.Group' in txt:
                print_numbered(
                    f"""In {pth}, you should change:\nform_model = models.Group\nto:\nform_model = 'group'"""
                )

            substrings = [
                'from otree.common',
                'from otree.constants',
                'from otree.models',
                'from otree.db',
            ]

            if any(substring in txt for substring in substrings):
                print_numbered(
                    f'{pth} imports non-API modules from otree. '
                    f'You should change the lines at the top to:\n{NEW_PAGES_PY_IMPORTS}'
                )

            if 'vars_for_all_templates' in txt:
                print_numbered(f'{pth}: vars_for_all_templates is not supported.')

        for pth in root.glob('*/templates/*/*.html'):
            txt = pth.read_text('utf8')
            if '{% extends "global/Base.html" %}' in txt:
                print_numbered(
                    f'{pth} ' + 'starts with {% extends "global/Base.html" %}. '
                    'You should replace that with {% extends "global/Page.html" %}'
                )
            if 'with label=' in txt:
                print_numbered(
                    str(pth)
                    + ': the formfield tag should not use "with label=". Just change it to "label=" '
                )

        custom_css_pth = Path('_static/global/custom.css')
        if custom_css_pth.exists():
            for line in custom_css_pth.open(encoding='utf8'):
                if line.startswith('input {'):
                    print_numbered(
                        f'{custom_css_pth}: you should delete the styling for "input" (or just delete all file contents)'
                    )

        print_function('Done. all files checked.')
