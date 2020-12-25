from pathlib import Path

import otree
from otree import settings
from starlette.responses import HTMLResponse

from .errors import TemplateLoadError


class FileLoader:
    def __init__(self, *dirs):
        self.dirs = dirs
        self.cache = {}

    def __call__(self, filename: str):
        if filename in self.cache:
            return self.cache[filename]

        template, path = self.load_template(filename)
        self.cache[filename] = template
        return template

    def search_template(self, template_id) -> Path:
        for dir in self.dirs:
            path = Path(dir, template_id)
            if path.exists():
                return path
        msg = f"Loader cannot locate the template file '{template_id}'."
        raise TemplateLoadError(msg)

    def load_template(self, template_id) -> tuple:
        from .template import Template  # todo: resolve circular import

        abspath = self.search_template(template_id)
        try:
            template_string = abspath.read_text('utf-8')
        except OSError as err:
            msg = f"FileLoader cannot load the template file '{abspath}'."
            raise TemplateLoadError(msg) from err
        template = Template(template_string, template_id)
        return template, abspath


class FileReloader(FileLoader):
    def __call__(self, template_id: str):
        if template_id in self.cache:
            cached_mtime, cached_path, cached_template = self.cache[template_id]
            if cached_path.exists() and cached_path.stat().st_mtime == cached_mtime:
                return cached_template
        template, path = self.load_template(template_id)
        mtime = path.stat().st_mtime
        self.cache[template_id] = (mtime, path, template)
        return template


def get_ibis_loader():
    loader_class = FileReloader if settings.DEBUG else FileLoader
    dirs = [Path(otree.__file__).parent.joinpath('templates'), Path('_templates'),] + [
        Path(app_name, 'templates') for app_name in settings.OTREE_APPS
    ]
    return loader_class(*dirs)


ibis_loader = get_ibis_loader()


def get_template_name_if_exists(template_names) -> str:
    '''return the path of the first template that exists'''
    for fname in template_names:
        try:
            ibis_loader(fname)
        except TemplateLoadError:
            pass
        else:
            return fname
    raise TemplateLoadError(str(template_names))


def render(template_name, context, **extra_context):
    return HTMLResponse(
        ibis_loader(template_name).render(context, **extra_context, strict_mode=True)
    )
    # i used to modify the traceback to report the original error,
    # but actually i think we shouldn't.
    # The main case I had in mind was if the user calls a method like
    # player.foo(), but it's simpler if they just don't call any complex methods
    # to begin with, and just pass variables to the template.
    # that way we don't go against thre grain