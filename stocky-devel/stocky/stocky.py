# The stocky main program using Flask socket
# See the runserver.sh script in this directory for how to launch the program.


import datetime as dt

import logging.config
import flask
from flask_sockets import Sockets

from gevent.queue import Queue

from geventwebsocket import websocket

import serverlib.serverconfig as serverconfig
import serverlib.commlink as commlink
import serverlib.TLSAscii as TLSAscii
import serverlib.QAILib as QAILib
import serverlib.Taskmeister as Taskmeister

from webclient.commonmsg import CommonMSG


# NOTE: initial ideas for this program were taken from
# random number thread -- BUT that was for flask socketIO, NOT flask sockets
# https://github.com/shanealynn/async_flask/blob/master/application.py


class serverclass:
    """The class that implements the web server. It is instantiated as a singleton."""

    def __init__(self, app: flask.Flask, CommLinkClass, cfgname: str) -> None:
        # must set logging  before anything else...
        self._app = app
        self.logger = app.logger

        self.logger.info("serverclass: reading config file '{}'".format(cfgname))
        self.cfg_dct = serverconfig.read_server_config(cfgname)
        self.cfg_dct['logger'] = self.logger
        self.logger.debug("serverclass: config file read...{}".format(self.cfg_dct))
        self.name = "Johnny"
        self.msgQ = Queue()
        self.logger.debug("serverclass: instantiating CommLinkClass...")
        self.cl = CommLinkClass('myservercl', self.cfg_dct)
        if self.cl.is_alive():
            self.logger.debug("Commlink is alive")
        else:
            msg = "Commlink is NOT alive, exiting"
            self.logger.info(msg)
            raise RuntimeError(msg)
        self.logger.debug("serverclass: getting id_string...")
        idstr = self.cl.id_string()
        self.logger.info("Commlink is alive and idents as '{}'".format(idstr))
        self.tls = TLSAscii.TLSReader(self.msgQ, self.logger, self.cl)
        self.BT_init_reader()

    def send_WS_msg(self, msg: CommonMSG) -> None:
        """Send a command to the web client over websocket in a standard JSON format."""
        self.ws.send(QAILib.tojson(msg.as_dict()))

    def BT_init_reader(self):
        """Initialise the RFID reader. Raise an exception if this fails."""
        # set RFID region
        reg_code = self.cfg_dct['RFID_REGION_CODE']
        self.logger.debug("setting RFID region '{}'".format(reg_code))
        self.tls.set_region(reg_code)
        # set date and time to local time.
        utc_t = dt.datetime.now()
        tz_info = self.cfg_dct['TZINFO']
        loc_t = utc_t.astimezone(tz_info)
        self.logger.debug("setting RFID date/time to '{}'".format(loc_t))
        self.tls.set_date_time(loc_t.year, loc_t.month, loc_t.day,
                               loc_t.hour, loc_t.minute, loc_t.second)

    def mainloop(self, ws: websocket):
        # the set of messages we simply pass on to the web client.
        MSG_FOR_WC_SET = frozenset([CommonMSG.MSG_SV_RAND_NUM,
                                    CommonMSG.MSG_SV_USB_STATE_CHANGE,
                                    CommonMSG.MSG_RF_STOCK_DATA,
                                    CommonMSG.MSG_RF_RADAR_DATA])

        # the set of messages to send to the TLS class (the RFID reader)
        MSG_FOR_RFID_SET = frozenset([CommonMSG.MSG_WC_STOCK_CHECK,
                                      CommonMSG.MSG_WC_RADAR_MODE])

        self.ws = ws
        # self.b = USBProc.USBProc(self.cfg_dct['USB_TUPLE'])
        # self.b.reg_CB(self.usb_state_change)
        # start a random generator thread
        self.randTM = Taskmeister.RandomGenerator(self.msgQ, self.logger)
        self.randTM.start_job()

        # start a websocket reader thread
        self.websocketTM = Taskmeister.WebSocketReader(self.msgQ, self.logger, ws)
        self.websocketTM.start_job()

        # start the previously initialised  bluetooth reader thread
        self.tls.start_job()

        while True:
            msg: CommonMSG = self.msgQ.get()
            self.logger.debug("handling msgtype '{}'".format(msg.msg))
            is_handled = False
            if msg.msg in MSG_FOR_WC_SET:
                is_handled = True
                self.send_WS_msg(msg)
            if msg.msg in MSG_FOR_RFID_SET:
                is_handled = True
                self.tls.send_RFID_msg(msg)
            if not is_handled:
                self.logger.debug("server NOT handling msgtype '{}'".format(msg.msg))

    def usb_state_change(self, newstate):
        """This routine is called whenever the USB device (the bluetooth dongle)
        is removed or plugged in.
        We pass this information to the web client so that it can show the device status.
        """
        # st = self.b.get_state()
        print("USB state is {}".format(newstate))
        self.send_WS_msg(CommonMSG(CommonMSG.MSG_SV_USB_STATE_CHANGE, newstate))


def test_logging(l):
    """Ensure that the logging configuration is what we think it is.
    This routine is disabled during normal operations.
    """
    ld = logging.Logger.manager.loggerDict
    print("loggernames {}".format(ld.keys()))
    for k, v in ld.items():
        if v == app.logger:
            print("app logger is called '{}'".format(k))
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
# test_logging(app.logger)
socky = Sockets(app)
# app.logger.debug('hoity toity')


def init_app(cfgname: str):
    """This routine is used a helper in order to launch the serverclass with the
    name of a configuration file, e.g. in a launching shell script, such as runserver.sh,
    we would write something like:
    gunicorn -k flask_sockets.worker "stocky:init_app('scoconfig.yaml')" --bind 0.0.0.0:5000
    """
    global the_main
    the_main = serverclass(app, commlink.SerialCommLink, cfgname)
    logging.config.dictConfig(serverconfig.read_logging_config('logging.yaml'))
    return app


# this launches the server main program in response to webclient program starting in the browser
@socky.route('/goo')
def goo(ws: websocket):
    the_main.mainloop(ws)


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
