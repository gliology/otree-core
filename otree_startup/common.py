from urllib.request import urlopen
import http.client
import urllib.error


def terminate_through_http(PORT):
    try:
        urlopen(f'http://localhost:{PORT}/KillZipServer/', data=b'foo')
    except (http.client.RemoteDisconnected, urllib.error.URLError):
        # - by design, RemoteDisconnected will happen because it sys.exit()
        # before returning an HttpResponse
        # - URLError may happen if the server didn't even start up yet
        #  (if you stop it right away)
        pass
