# The stocky web server main program using Flask socket
# See the runserver.sh script in this directory for how to launch the program.

import typing

from geventwebsocket import websocket
import serverlib.serverconfig as serverconfig
import serverlib.commlink as commlink
import serverlib.stockyserver as stockyserver
import serverlib.ServerWebSocket as ServerWebSocket

# import logging
import logging.config
import flask
from flask_sockets import Sockets


def get_logger_name(mylogger) -> str:
    ld = logging.Logger.manager.loggerDict
    # ld = logman.loggerDict
    # print("loggernames {}".format(ld.keys()))
    for k, v in ld.items():
        if v == mylogger:
            return k
    return 'not found'


def test_logging(l):
    """Ensure that the logging configuration is what we think it is.
    This routine is disabled during normal operations.
    """
    print("app logger is called '{}'".format(get_logger_name(app.logger)))
    print("EFF LEVEL {}".format(l.getEffectiveLevel()))
    print("LL is {}".format(l))
    l.debug("debug level")
    l.info("info level")
    l.warn("warn level")
    l.error("error level")
    l.critical("critical level")


class stockyapp(flask.Flask):
    def __init__(self):
        super().__init__(__name__.split('.')[0])

    def app_protocol(self, unused) -> str:
        """This method is called by geventwebsocket (handler.py) in order to set the
        websocket protocol.
        The name of the method is significant (it must be called exactly this)
        The websocket protocol must be defined, or the server will not respond correctly
        (missing Sec-WebSocket-Protocol entry in the response header)
        and this will crash the stocky webclient when it is run under chrome.
        NOTE: the websocket protocol is hardcoded to be 'json' on the webclient side.
        """
        return 'json'


logging.config.dictConfig(serverconfig.read_logging_config('logging.yaml'))
app: typing.Optional[stockyapp] = stockyapp()
socky: typing.Optional[Sockets] = Sockets(app)
the_main: typing.Optional[stockyserver.StockyServer] = None


def init_app(cfgname: str) -> flask.Flask:
    """This routine is used as a helper in order to launch the serverclass with the
    name of a configuration file, e.g. in a launching shell script, such as runserver.sh,
    we would write something like:
    gunicorn -k flask_sockets.worker "stocky:init_app('scoconfig.yaml')" --bind 0.0.0.0:5000
    """
    print("hello from init_app")
    global the_main
    # test_logging(app.logger)
    the_main = stockyserver.StockyServer(app, commlink.SerialCommLink, cfgname)
    # logging.config.dictConfig(serverconfig.read_logging_config('logging.yaml'))
    print("goodbye from init_app")
    return app


# this launches the stocky server main program in response to the webclient program running in
# the browser opening a websocket connection. The server-side websocket connection
# used for communication with the webclient is passed in from flask_sockets.
@socky.route('/goo')
def goo(rawws: websocket):
    # print("bla before '{}'".format(rawws))
    ws = ServerWebSocket.JSONWebSocket(rawws, app.logger)
    print("goo: got a websocket")
    if the_main is not None:
        the_main.set_websocket(ws)
        print("goo: entering mainloop")
        the_main.mainloop()
        print("goo: exited mainloop")
    else:
        print('the_main is None!')


# this launches the RFID_Ping_Server in response to the webclient program running in
# the browser opening a websocket connection. The server-side websocket connection
# used for communication with the webclient is passed in from flask_sockets.
@socky.route('/rfidping')
def rfid_pinger(rawws: websocket):
    # print("bla before '{}'".format(rawws))
    ws = ServerWebSocket.JSONWebSocket(rawws, app.logger)
    my_server = stockyserver.RFID_Ping_Server(app, "RFIDPinger")
    print("goo: got a websocket")
    my_server.set_websocket(ws)
    print("goo: entering mainloop")
    my_server.mainloop()
    print("goo: exited mainloop")


# this is required to serve the javascript code
@app.route('/webclient/__target__/<path:path>')
def send_js(path):
    return flask.send_from_directory('webclient/__target__', path)


# serve the main page
@app.route('/')
def main_page():
    return flask.render_template('mainpage.html')


if __name__ == "__main__":
    print("Sorry Dave, stocky.py main program will not run....")
    print("Start the stocky server using the runserver.sh script")
    print("""Or something like:
'gunicorn -k flask_sockets.worker "stocky:init_app('serverconfig.yaml')" --bind 0.0.0.0:5000'""")
