from urllib.request import urlopen
import http.client
import urllib.error


def terminate_through_http(PORT):
    try:
        # send data= so it makes a post request
        urlopen(f'http://localhost:{PORT}/TerminateServer/', data=b'foo')
    except (
        http.client.RemoteDisconnected,
        urllib.error.URLError,
        ConnectionResetError,
    ) as exc:
        # - URLError may happen if the server didn't even start up yet
        #  (if you stop it right away)
        # - RemoteDisconnected & ConnectionResetError apparently happen if the server exits
        # before returning an HttpResponse.
        pass
