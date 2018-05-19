# The stocky main program using Flask socket
# See the runserver.sh script in this directory for how to launch the program.



from geventwebsocket import websocket
import serverlib.serverconfig as serverconfig
import serverlib.commlink as commlink
import serverlib.stockyserver as stockyserver

import logging
import logging.config
# import logging.Logger.manager as logman
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


logging.config.dictConfig(serverconfig.read_logging_config('logging.yaml'))
the_main = None
app = flask.Flask(__name__.split('.')[0])
test_logging(app.logger)
socky = Sockets(app)
# app.logger.debug('hoity toity')


def init_app(cfgname: str):
    """This routine is used a helper in order to launch the serverclass with the
    name of a configuration file, e.g. in a launching shell script, such as runserver.sh,
    we would write something like:
    gunicorn -k flask_sockets.worker "stocky:init_app('scoconfig.yaml')" --bind 0.0.0.0:5000
    """
    global the_main
    the_main = stockyserver.serverclass(app, commlink.SerialCommLink, cfgname)
    # logging.config.dictConfig(serverconfig.read_logging_config('logging.yaml'))
    return app


# this launches the server main program in response to the webclient program starting
# in the browser
@socky.route('/goo')
def goo(ws: websocket):
    if the_main is not None:
        the_main.mainloop(ws)
    else:
        print('the_main is None!')


# this is required to serve the javascript code
@app.route('/webclient/__javascript__/<path:path>')
def send_js(path):
    return flask.send_from_directory('webclient/__javascript__', path)


# serve the main page
@app.route('/')
def main_page():
    return flask.render_template('mainpage.html')


if __name__ == "__main__":
    print("Sorry Dave, stocky.py main program will not run....")
    print("Start the stocky server using the runserver.sh script")
    print("""Or something like:
'gunicorn -k flask_sockets.worker "stocky:init_app('serverconfig.yaml')" --bind 0.0.0.0:5000'""")
