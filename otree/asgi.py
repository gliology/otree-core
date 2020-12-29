from starlette.applications import Starlette
from . import settings
from .urls import routes
from .middleware import middlewares
from starlette.middleware import Middleware
from .errorpage import OTreeServerErrorMiddleware
from starlette.routing import NoMatchFound
from starlette.responses import HTMLResponse
from otree.database import save_sqlite_db
from .patch import ExceptionMiddleware


class OTreeStarlette(Starlette):
    def build_middleware_stack(self):
        debug = self.debug
        error_handler = None
        exception_handlers = {}

        for key, value in self.exception_handlers.items():
            if key in (500, Exception):
                error_handler = value
            else:
                exception_handlers[key] = value

        middleware = (
            [Middleware(OTreeServerErrorMiddleware, handler=error_handler, debug=debug)]
            + self.user_middleware
            + [
                Middleware(
                    ExceptionMiddleware, handlers=exception_handlers, debug=debug
                )
            ]
        )

        app = self.router
        for cls, options in reversed(middleware):
            app = cls(app=app, **options)
        return app


ERR_500 = 500


async def server_error(request, exc):
    return HTMLResponse(content=HTML_500_PAGE, status_code=ERR_500)


app = OTreeStarlette(
    debug=settings.DEBUG,
    routes=routes,
    middleware=middlewares,
    exception_handlers={ERR_500: server_error},
    on_shutdown=[save_sqlite_db],
)

# alias like django reverse()
def reverse(name, **path_params):
    try:
        return app.url_path_for(name, **path_params)
    except NoMatchFound as exc:
        raise NoMatchFound(f'{name}, {path_params}') from None


HTML_500_PAGE = """<!DOCTYPE html>
<html>
<head>
    <title>Server Error (500)</title>
</head>
<body>

<h2>Server Error (500)</h2>

<p>
  For security reasons, the error message is not displayed here.
  You can view it with one of the below techniques:
</p>

<ul>
    <li>Delete the <code>OTREE_PRODUCTION</code> environment variable and reload this page</li>
    <li>Look at your Sentry messages (see the docs on how to enable Sentry)</li>
    <li>Look at the server logs</li>
</ul>

</body>
</html>"""
