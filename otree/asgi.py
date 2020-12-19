from starlette.applications import Starlette
from . import settings
from .urls import routes
from .middleware import middlewares
from starlette.middleware import Middleware
from starlette.exceptions import ExceptionMiddleware
from .errorpage import OTreeServerErrorMiddleware
from starlette.routing import NoMatchFound


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


app = OTreeStarlette(debug=settings.DEBUG, routes=routes, middleware=middlewares)

# alias like django reverse()
def reverse(name, **path_params):
    try:
        return app.url_path_for(name, **path_params)
    except NoMatchFound as exc:
        raise NoMatchFound(f'{name}, {path_params}') from None
