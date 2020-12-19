import html
import inspect
import traceback
import os
from otree.templating.compiler import Token
from otree.templating.errors import (
    TemplateError,
    TemplateRenderingError,
    TemplateLexingError,
    ErrorWithToken,
)
from starlette.middleware.errors import ServerErrorMiddleware, STYLES, JS
from pathlib import Path
from otree.templating.loader import ibis_loader

CWD_PATH = Path(os.getcwd())

IBIS_LINE = """
<p><span class="frame-line">
<span class="lineno">{lineno}.</span> {line}</span></p>
"""

IBIS_CENTER_LINE = """
<p class="center-line"><span class="frame-line center-line">
<span class="lineno">{lineno}.</span> {line}</span></p>
"""

IBIS_TEMPLATE = """
<div class="ibis-error">
    <p class="frame-title">File <span class="frame-filename">{template_id}</span>,
    line <i>{line_number}</i>,
    in <b>{tag_name}</b>
    <div class="source-code">{code_context}</div>
</div>

"""

FRAME_TEMPLATE = """
<div>
    <p class="frame-title">File <span class="frame-filename">{frame_filename}</span>,
    line <i>{frame_lineno}</i>,
    in <b>{frame_name}</b>
    <span class="collapse-btn" data-frame-id="{frame_filename}-{frame_lineno}" onclick="collapse(this)">{collapse_button}</span>
    </p>
    <div id="{frame_filename}-{frame_lineno}" class="source-code {collapsed}">
    {code_context}
    {locals_table}
    </div>
</div>
"""  # noqa: E501


TEMPLATE = """
<html>
    <head>
        <style type='text/css'>
            {styles}
            {otree_styles}
        </style>
        <title>500 Server Error</title>
    </head>
    <body>
        <h2>{error}</h2>
        {ibis_html}
        <div class="traceback-container">
            <p class="traceback-title">Traceback</p>
            <div>{exc_html}</div>
        </div>
        {js}
    </body>
</html>
"""

OTREE_STYLES = """
.locals-table {
  border-collapse: collapse;
}

.locals-table td, th {
  border: 1px solid #999;
  padding: 0.5rem;
  text-align: left;
}
"""


class OTreeServerErrorMiddleware(ServerErrorMiddleware):
    def generate_ibis_html(self, template_id, line_number, tag_name=""):
        path = ibis_loader.search_template(template_id)

        html_lines = []
        for i, line in enumerate(path.open(encoding='utf-8'), start=1):

            if (i >= line_number - 3) and (i <= line_number + 3):
                values = {
                    # HTML escape - line could contain < or >
                    "line": html.escape(line).replace(" ", "&nbsp"),
                    "lineno": i,
                }
                tpl = IBIS_CENTER_LINE if i == line_number else IBIS_LINE
                html_lines.append(tpl.format(**values))
        return IBIS_TEMPLATE.format(
            template_id=template_id,
            line_number=line_number,
            tag_name=tag_name,
            code_context=''.join(html_lines),
        )

    def generate_html(self, exc: Exception, limit: int = 7) -> str:
        if isinstance(exc, ErrorWithToken):
            token = exc.token
            ibis_html = self.generate_ibis_html(
                template_id=token.template_id,
                line_number=token.line_number,
                tag_name=token.keyword,
            )
        elif isinstance(exc, TemplateLexingError):
            ibis_html = self.generate_ibis_html(
                template_id=exc.template_id, line_number=exc.line_number
            )
        else:
            ibis_html = ''

        while isinstance(exc, TemplateRenderingError) and exc.__cause__:
            exc = exc.__cause__

        traceback_obj = traceback.TracebackException.from_exception(
            exc, capture_locals=True
        )
        frames = inspect.getinnerframes(
            traceback_obj.exc_traceback, limit  # type: ignore
        )

        exc_html = ""
        for frame in reversed(frames):
            # if it's in the user's project, except for a venv folder
            is_expanded = (
                CWD_PATH in Path(frame.filename).parents
                and not 'site-packages' in frame.filename
            )
            exc_html += self.generate_frame_html(frame, is_expanded)

        # escape error class and text
        error = (
            f"{html.escape(traceback_obj.exc_type.__name__)}: "
            f"{html.escape(str(traceback_obj))}"
        )

        return TEMPLATE.format(
            styles=STYLES,
            js=JS,
            error=error,
            exc_html=exc_html,
            ibis_html=ibis_html,
            otree_styles=OTREE_STYLES,
        )

    def generate_frame_html(self, frame: inspect.FrameInfo, is_expanded: bool) -> str:
        code_context = "".join(
            self.format_line(index, line, frame.lineno, frame.index)  # type: ignore
            for index, line in enumerate(frame.code_context or [])
        )

        # only show locals if is expanded. reduces the risk of issues happening during __repr__
        if is_expanded:
            try:
                locals = []
                for k, v in frame.frame.f_locals.items():
                    if k not in ['self']:
                        locals.append(f'<tr><th>{k}</th><td>{repr(v)[:50]}</td></tr>')
                locals_table = (
                    '<table class="locals-table source-code">'
                    + ''.join(locals)
                    + '</table>'
                )
            except Exception:
                locals_table = ''
        else:
            locals_table = ''
        values = {
            # HTML escape - filename could contain < or >, especially if it's a virtual
            # file e.g. <stdin> in the REPL
            "frame_filename": html.escape(frame.filename),
            "frame_lineno": frame.lineno,
            # HTML escape - if you try very hard it's possible to name a function with <
            # or >
            "frame_name": html.escape(frame.function),
            "code_context": code_context,
            "collapsed": "" if is_expanded else "collapsed",
            "collapse_button": "&#8210;" if is_expanded else "+",
            "locals_table": locals_table,
        }
        return FRAME_TEMPLATE.format(**values)
