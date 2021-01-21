from .base import BaseCommand
from pathlib import Path
import re

try:

    import rope.base.codeanalyze
    import rope.refactor.occurrences
    from rope.refactor import rename, move
    from rope.refactor.rename import Rename
    from rope.base.project import Project
    from rope.base.libutils import path_to_resource
    import black
except ModuleNotFoundError:
    import sys

    sys.exit('Before running this command, you need to run "pip3 install black rope" ')
from rope.refactor.importutils import ImportTools
from collections import namedtuple
from typing import Iterable

print_function = print

MethodInfo = namedtuple('MethodInfo', ['start', 'stop', 'name', 'model'])


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('apps', nargs='*')

    def handle(self, *args, apps, **options):
        for app in Path('.').iterdir():
            if app.is_dir() and app.joinpath('models.py').exists():
                if apps and app.name not in apps:
                    continue
                try:
                    make_noself(app.name)
                except Exception as exc:
                    app.joinpath('app.py').unlink(missing_ok=True)
                    raise


class CannotConvert(Exception):
    pass


def make_noself(app_name):
    proj = Project(app_name, ropefolder=None)
    approot = Path(app_name)
    app_path = approot / 'app.py'
    pages_path = approot / 'pages.py'
    models_path = approot / 'models.py'
    if not models_path.exists():
        return
    print_function('Upgrading', app_name)

    def read():
        return app_path.read_text('utf8')

    def write(txt):
        app_path.write_text(txt, encoding='utf8')

    def writelines(lines):
        write('\n'.join(lines))

    END_OF_MODELS = '"""endofmodels"""'
    lines = [
        'from otree.api import Page, WaitPage',
        *models_path.read_text('utf8').splitlines(),
        END_OF_MODELS,
    ]

    pages_txt = pages_path.read_text('utf8')

    m = re.search(
        r'self\.(?!player|group|subsession|participant|session|timeout_happened|round_number)(\w+)',
        pages_txt,
    )
    if m:
        msg = f"""{app_name}/pages.py contains "{m.group(0)}". This is not a recognized page attribute."""
        raise CannotConvert(msg)

    for line in pages_txt.split('\n'):
        if line.startswith('from ._builtin'):
            continue
        if line.startswith('from .models'):
            continue

        lines.append(line)

    writelines(lines)

    # normalize, get rid of empty lines
    lines = app_path.read_text('utf8').splitlines(keepends=False)
    writelines(e.replace('\t', ' ' * 4) for e in lines if e.strip())

    def resource(pth):
        return path_to_resource(proj, app_name + '/' + pth)

    app_res = resource('app.py')

    app_txt = read()

    # need it to be reversed so we don't shift everything down
    class_names = list(
        m.group(1)
        for m in re.finditer(
            r'^class (\w+)\((BasePlayer|BaseGroup|BaseSubsession|Page|WaitPage)',
            app_txt,
            re.MULTILINE,
        )
    )

    for ClassName in reversed(class_names):
        offsets = get_method_offsets(app_txt, ClassName)
        rename_self_to = dict(
            Player='player', Group='group', Subsession='subsession'
        ).get(ClassName, 'player')
        for offset in reversed(offsets):
            # it might be error_message or app_after_this_page, which take extra args.
            self_offset = offset + app_txt[offset:].index('(self') + 2
            try:
                changes = Rename(proj, app_res, self_offset).get_changes(rename_self_to)
                proj.do(changes)
            except Exception:
                print_function(app_txt[self_offset : self_offset + 30])
                raise

    import_tools = ImportTools(proj)

    rope_module = proj.get_module('app')
    module_with_imports = import_tools.module_imports(rope_module)
    module_with_imports.remove_duplicates()
    module_with_imports.sort_imports()
    write(module_with_imports.get_changed_source())

    lines = read().splitlines()

    method_bounds = []
    for ClassName in class_names:
        if ClassName in ['Player', 'Group', 'Subsession']:
            # print_function(ClassName, list(get_method_bounds(lines, ClassName)))
            method_bounds.extend(get_method_bounds(lines, ClassName, start_index=0))
        else:
            # rename page methods to something unique and set the attribute,
            # e.g. is_displayed = is_displayed1
            for start, end, name, _ in reversed(
                list(get_method_bounds(lines, ClassName, start_index=0))
            ):
                if name == 'after_all_players_arrive':
                    print(
                        f'{app_name}: skipping after_all_players_arrive because it still uses the 2018 format'
                    )
                    continue
                lines.insert(start, f'    @staticmethod')

    # return
    function_lines = ['# FUNCTIONS']
    non_function_lines = []

    i = 0
    for bound in method_bounds:
        non_function_lines.extend(lines[i : bound.start])
        function_lines.extend(
            dedent(line) for line in lines[bound.start : bound.stop + 1]
        )
        i = bound.stop + 1
    non_function_lines.extend(lines[i:])

    # not aapa, since we need to resolve it being defined on group vs subsession.
    for i, line in enumerate(non_function_lines):
        non_function_lines[i] = re.sub(
            r"""(live_method) = ["'](\w+)["']""", r'\1 = \2', line,
        )

    function_lines.append('# PAGES')
    function_txt = '\n'.join(function_lines)

    txt = '\n'.join(non_function_lines).replace(END_OF_MODELS, function_txt)

    txt = (
        txt.replace('player.player.', 'player.')
        .replace(
            'def before_next_page(player):',
            'def before_next_page(player, timeout_happened):',
        )
        .replace('player.timeout_happened', 'timeout_happened')
    )

    # add type annotations
    # some functions have multiple args, like error_message
    txt = re.sub(r'def (\w+)\(player\b', r'def \1(player: Player', txt)
    txt = re.sub(r'def (\w+)\(group\b', r'def \1(group: Group', txt)
    txt = re.sub(r'def (\w+)\(subsession\b', r'def \1(subsession: Subsession', txt)

    lines = txt.splitlines(keepends=False)

    # add missing 'pass' for empty classes
    lines2 = []
    for i in range(len(lines)):
        lines2.append(lines[i])
        if lines[i].startswith('class ') and not lines[i + 1].startswith(' '):
            lines2.append(' ' * 4 + 'pass')

    write(black_format('\n'.join(lines2)))

    tests_path = approot.joinpath('tests.py')
    if tests_path.exists():

        tests_txt = tests_path.read_text('utf8')
        new_txt = (
            tests_txt.replace('from ._builtin import Bot', 'from otree.api import Bot')
            .replace('from . import pages', 'from . import app')
            .replace('from .models import Constants', 'from .app import Constants')
        )
        new_txt = re.sub(r'\bpages.(\w)', r'app.\1', new_txt)
        approot.joinpath('tests_noself.py').write_text(new_txt, encoding='utf8')


def dedent(line):
    if line.startswith(' ' * 4):
        return line[4:]
    return line


def black_format(txt):
    return black.format_str(
        txt, mode=black.Mode(line_length=100, string_normalization=False)
    )


def is_within_a_bound(bounds, lineno):
    for bound in bounds:
        if bound.start <= lineno <= bound.stop:
            return True


def get_method_bounds(lines, ModelName, start_index=1) -> Iterable[MethodInfo]:
    """1 based"""
    in_model = False

    start = None
    name = None
    model = None
    # use start=1 to match line numbers in text editor
    for lineno, line in enumerate(lines, start=start_index):
        if line.startswith(f'class {ModelName}('):
            in_model = True
            continue

        if in_model:

            if is_class_or_module_level_statement(line):
                if start:
                    yield MethodInfo(start, lineno - 1, name, model)
                    start = None
                if line.startswith('    def '):
                    start = lineno
                    m = re.search(r'def (\w+)\((\w+)', line)
                    name = m.group(1)
                    model = m.group(2)

            if is_module_level_statement(line):
                return


def is_class_or_module_level_statement(line):
    return line[:5].strip() and not line[:5].strip().startswith('#')


def is_module_level_statement(line):
    return line[:1].strip() and not line[:1].strip().startswith('#')


def get_method_offsets(txt, ClassName):
    import re

    class_start = txt.index(f'\nclass {ClassName}(')
    m = list(re.finditer(r'^\w', txt[class_start:], re.MULTILINE))[1]
    class_end = class_start + m.start()
    return [
        m.start()
        for m in re.finditer(r'^\s{4}def \w+\(self\b', txt, re.MULTILINE)
        if class_start < m.start() < class_end
    ]
