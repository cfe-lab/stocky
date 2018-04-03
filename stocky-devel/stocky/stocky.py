# The stocky main program using Flask socket
# See the runserver.sh script in this directory for how to launch the program.


import typing
import datetime as dt

import logging.config
import json
import flask
from flask_sockets import Sockets

import gevent
from gevent.queue import Queue

from geventwebsocket import websocket

import serverlib.serverconfig as serverconfig
import serverlib.USBProc as USBProc
import serverlib.commlink as commlink
import serverlib.TLSAscii as TLSAscii

from webclient.commonmsg import CommonMSG

from random import random


# NOTE: initial ideas for this program were taken from
# random number thread -- BUT that was for flask socketIO, NOT flask sockets
# https://github.com/shanealynn/async_flask/blob/master/application.py


def tojson(data) -> str:
    """Convert the data structure to json.
    see https://docs.python.org/3.4/library/json.html
    """
    return json.dumps(data, separators=(',', ':'))


def fromjson(data_str: str) -> typing.Any:
    """Convert a string into a data struct which we return."""
    return json.loads(data_str)


class serverclass:
    """The class that implements the web server. It is instantiated as a singleton."""

    def __init__(self, app: flask.Flask, CommLinkClass, cfgname: str) -> None:
        self.cfg_dct = serverconfig.read_server_config(cfgname)
        self._app = app
        self.logger = app.logger
        self.name = "Johnny"
        self.logger.info("serverclass: reading config file '{}'".format(cfgname))
        self.msgQ = Queue()
        self.cl = CommLinkClass('myservercl')
        if self.cl.is_alive():
            idstr = self.cl.id_string()
            self.logger.info("Commlink is alive and idents as '{}'".format(idstr))
        else:
            raise RuntimeError("Commlink is NOT alive, exiting")
        self.tls = TLSAscii.TLS(self.cl)

    def send_WS_msg(self, msg: CommonMSG) -> None:
        """Send a command to the web client over websocket in a standard JSON format."""
        self.ws.send(tojson(msg.as_dict()))

    def read_WS_msg(self) -> CommonMSG:
        """Block until a command is received from the webclient over websocket.
        Return the JSON string received as a CommonMSG instance."""
        dct = fromjson(self.ws.receive())
        return CommonMSG(dct['msg'], dct['data'])

    def enQ(self, msg: CommonMSG) -> None:
        """Put a message onto the server Queue"""
        self.msgQ.put(msg)

    def usb_state_change(self, newstate):
        """This routine is called whenever the USB device (the bluetooth dongle)
        is removed or plugged in.
        We pass this information to the web client so that it can show the device status.
        """
        # st = self.b.get_state()
        print("USB state is {}".format(newstate))
        self.send_WS_msg(CommonMSG(CommonMSG.MSG_USB_STATE_CHANGE, newstate))

    def random_worker(self):
        while True:
            number = round(random()*10, 3)
            self.logger.debug("random: {} {}".format(self.name, number))
            self.enQ(CommonMSG(CommonMSG.MSG_RAND_NUM, number))
            # send_msg(self.ws, 'number', number)
            gevent.sleep(1)

    def WS_reader(self) -> None:
        """The websocket reader process.
        Read a message from the web client and put it on the queue.
        """
        while True:
            self.enQ(self.read_WS_msg())

    def BT_reader(self) -> None:
        """The bluetooth reader process.
        We read from the TLS commands on the commlink, translate them
        and send the resulting data/commands to the Queue.
        """
        while True:
            self.enQ(self.tls.read_TLS_msg())

    def BT_init_reader(self):
        """Initialise the RFID reader. Raise an exception if this fails."""
        # set RFID region
        reg_code = self.cfg_dct['RFID_REGION_CODE']
        self.logger.debug("setting RFID region '{}'".format(reg_code))
        self.tls.set_region(reg_code)
        # set date and time to local time.
        loc_t = dt.datetime.now()
        self.logger.debug("setting RFID date/time to '{}'".format(loc_t))
        self.tls.set_date_time(loc_t.year, loc_t.month, loc_t.day,
                               loc_t.hour, loc_t.minute, loc_t.second)

    def BT_set_stock_check_mode(self):
        """Set the RFID read in stock taking mode."""
        # self.tls.
        pass

    def mainloop(self, ws: websocket):
        # the set of messages we simply pass on to the web client.
        MSG_FOR_WC_SET = frozenset([CommonMSG.MSG_RAND_NUM, CommonMSG.MSG_USB_STATE_CHANGE])

        self.ws = ws
        self.b = USBProc.USBProc(self.cfg_dct['USB_TUPLE'])
        self.BT_init_reader()

        self.b.reg_CB(self.usb_state_change)
        gevent.spawn(self.random_worker)
        gevent.spawn(self.WS_reader)
        while True:
            msg: CommonMSG = self.msgQ.get()
            if msg.msg in MSG_FOR_WC_SET:
                self.send_WS_msg(msg)
            else:
                self.logger.debug("handling msgtype '{}'".format(msg.msg))
                if msg.msg == CommonMSG.MSG_WC_STOCK_CHECK:
                    self.BT_set_stock_check_mode()


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
    the_main = serverclass(app, commlink.DummyCommLink, cfgname)
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
