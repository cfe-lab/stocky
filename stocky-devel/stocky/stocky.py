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

AVENUM = 5


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
        self.cl = CommLinkClass(self.cfg_dct)
        if self.cl.is_alive():
            self.logger.debug("Commlink is alive")
        else:
            msg = "Commlink is NOT alive, exiting"
            self.logger.info(msg)
            raise RuntimeError(msg)
        self.logger.debug("serverclass: getting id_string...")
        idstr = self.cl.id_string()
        self.logger.info("Commlink is alive and idents as '{}'".format(idstr))
        self.tls = TLSAscii.TLSReader(self.msgQ, self.logger, self.cl, AVENUM)
        self.BT_init_reader()

        # now: get our current stock list from QAI
        qai_url = self.cfg_dct['STOCK_LIST_URL']
        qai_file = self.cfg_dct['STOCK_LIST_FILE']
        self.logger.info("QAI info URL: '{}', file: '{}'".format(qai_url, qai_file))
        self.qaidata = QAILib.QAIdata(qai_url, qai_file)
        qai_has_data = self.qaidata.has_qai_data()
        self.logger.info("Before pull: QAI has data: {}".format(qai_has_data))
        if not qai_has_data:
            if not self.qaidata.pull_qai_data():
                raise RuntimeError("Failed to pull stock list from QAI")
            # we have the data from QAI, dump it for later use
            self.qaidata.dumpfileQAIdata()
        self.logger.info("After pull: QAI has data: {}".format(qai_has_data))

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

    def server_handle_msg(self, msg: CommonMSG) -> None:
        """Handle this message to me..."""
        if msg.msg == CommonMSG.MSG_WC_STOCK_CHECK:
            # the server is sending a list of all stock locations
            # in response to a MSG_WC_STOCK_CHECK
            self.timerTM.set_active(False)
            wc_stock_dct = self.qaidata.generate_webclient_stocklist()
            self.send_WS_msg(CommonMSG(CommonMSG.MSG_SV_NEW_STOCK_LIST, wc_stock_dct))
        elif msg.msg == CommonMSG.MSG_WC_RADAR_MODE:
            self.logger.debug("server in RADAR mode...")
            self.timerTM.set_active(True)
        elif CommonMSG.MSG_SV_TIMER_TICK:
            self.logger.debug("server received tick...")
            # print("MY logger is called '{}'".format(get_logger_name(self.logger)))
            if self.tls.is_in_radarmode():
                self.tls.RadarGet()
        else:
            self.logger.debug("server not handling message {}".format(msg))

    def mainloop(self, ws: websocket):
        # the set of messages we simply pass on to the web client.
        MSG_FOR_WC_SET = frozenset([CommonMSG.MSG_SV_RAND_NUM,
                                    CommonMSG.MSG_SV_USB_STATE_CHANGE,
                                    CommonMSG.MSG_RF_STOCK_DATA,
                                    CommonMSG.MSG_RF_RADAR_DATA])

        # the set of messages to send to the TLS class (the RFID reader)
        MSG_FOR_RFID_SET = frozenset([CommonMSG.MSG_WC_STOCK_CHECK,
                                      CommonMSG.MSG_WC_RADAR_MODE])

        # the set of messages the server should handle itself.
        MSG_FOR_ME_SET = frozenset([CommonMSG.MSG_WC_STOCK_CHECK,
                                    CommonMSG.MSG_WC_RADAR_MODE,
                                    CommonMSG.MSG_SV_TIMER_TICK])

        self.ws = ws
        # start a random generator thread
        # self.randTM = Taskmeister.RandomGenerator(self.msgQ, self.logger)
        # self.randTM.set_active(True)

        # create a timer tick for use in radar mode
        self.timerTM = Taskmeister.TickGenerator(self.msgQ, self.logger, 1, 'radartick')
        self.timerTM.set_active(False)

        # create a websocket reader thread
        self.websocketTM = Taskmeister.WebSocketReader(self.msgQ, self.logger, ws)

        while True:
            msg: CommonMSG = self.msgQ.get()
            self.logger.debug("handling msgtype '{}'".format(msg.msg))
            if msg.is_from_rfid_reader():
                self.logger.debug("GOT RFID {}".format(msg.as_dict()))
            is_handled = False
            if msg.msg in MSG_FOR_WC_SET:
                is_handled = True
                self.send_WS_msg(msg)
            if msg.msg in MSG_FOR_RFID_SET:
                is_handled = True
                self.tls.send_RFID_msg(msg)
            if msg.msg in MSG_FOR_ME_SET:
                is_handled = True
                self.server_handle_msg(msg)
            if not is_handled:
                self.logger.error("mainloop NOT handling msgtype '{}'".format(msg.msg))


def get_logger_name(mylogger) -> str:
    ld = logging.Logger.manager.loggerDict
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
    the_main = serverclass(app, commlink.SerialCommLink, cfgname)
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
