# import typing
import flask

import gevent
from gevent.queue import Queue
from geventwebsocket import websocket
import serverlib.timelib as timelib
import serverlib.TLSAscii as TLSAscii
import serverlib.qai_helper as qai_helper
import serverlib.ChemStock as ChemStock
import serverlib.Taskmeister as Taskmeister
import serverlib.serverconfig as serverconfig

from webclient.commonmsg import CommonMSG


# NOTE: initial ideas for this program were taken from
# random number thread -- BUT that was for flask socketIO, NOT flask sockets
# https://github.com/shanealynn/async_flask/blob/master/application.py

AVENUM = 5


class serverclass:
    """The class that implements the web server. It is instantiated as a singleton."""

    # the set of messages we simply pass on to the web client.
    MSG_FOR_WC_SET = frozenset([CommonMSG.MSG_SV_RAND_NUM,
                                CommonMSG.MSG_SV_USB_STATE_CHANGE,
                                CommonMSG.MSG_RF_STOCK_DATA,
                                CommonMSG.MSG_RF_RADAR_DATA,
                                CommonMSG.MSG_SV_RFID_STATREP,
                                CommonMSG.MSG_SV_RFID_ACTIVITY])

    # the set of messages to send to the TLS class (the RFID reader)
    MSG_FOR_RFID_SET = frozenset([CommonMSG.MSG_WC_STOCK_CHECK,
                                  CommonMSG.MSG_SV_GENERIC_COMMAND,
                                  CommonMSG.MSG_WC_RADAR_MODE])

    # the set of messages the server should handle itself.
    MSG_FOR_ME_SET = frozenset([CommonMSG.MSG_WC_STOCK_CHECK,
                                CommonMSG.MSG_WC_QAI_AUTH,
                                CommonMSG.MSG_WC_RADAR_MODE,
                                CommonMSG.MSG_WC_LOGIN_TRY,
                                CommonMSG.MSG_WC_LOGOUT_TRY,
                                CommonMSG.MSG_WC_SET_STOCK_LOCATION,
                                CommonMSG.MSG_SV_TIMER_TICK])

    def __init__(self, app: flask.Flask, CommLinkClass, cfgname: str) -> None:
        # must set logging  before anything else...
        self._app = app
        self.logger = app.logger

        self.logger.info("serverclass: reading config file '{}'".format(cfgname))
        self.cfg_dct = serverconfig.read_server_config(cfgname)
        self.cfg_dct['logger'] = self.logger
        self.logger.debug("serverclass: config file read...{}".format(self.cfg_dct))
        timelib.set_local_timezone(self.cfg_dct['TZINFO'])
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
        self.logger.info("Bluetooth init OK")

        # now: set up our channel to QAI
        self.qai_url = self.cfg_dct['QAI_URL']
        self.qai_file = self.cfg_dct['LOCAL_STOCK_DB_FILE']
        self.logger.info("QAI info URL: '{}', file: '{}'".format(self.qai_url, self.qai_file))
        self.qaisession = qai_helper.Session()
        self.stockdb = ChemStock.ChemStockDB(self.qai_file)
        # now: get our current stock list from QAI

        # create a timer tick for use in radar mode
        self.timerTM = Taskmeister.TickGenerator(self.msgQ, self.logger, 1, 'radartick')
        self.timerTM.set_active(False)
        self.logger.info("End of serverclass.__init__")

    def send_WS_msg(self, msg: CommonMSG) -> None:
        """Send a command to the web client over websocket in a standard JSON format."""
        if self.ws is not None:
            self.ws.send(qai_helper.tojson(msg.as_dict()))

    def sleep(self, secs: int) -> None:
        gevent.sleep(secs)

    def BT_init_reader(self):
        """Initialise the RFID reader. Raise an exception if this fails."""
        # set RFID region
        reg_code = self.cfg_dct['RFID_REGION_CODE']
        self.logger.debug("setting RFID region '{}'".format(reg_code))
        self.tls.set_region(reg_code)
        # set date and time to local time.
        loc_t = timelib.loc_nowtime()
        self.logger.debug("setting RFID date/time to '{}'".format(loc_t))
        self.tls.set_date_time(loc_t.year, loc_t.month, loc_t.day,
                               loc_t.hour, loc_t.minute, loc_t.second)

    def server_handle_msg(self, msg: CommonMSG) -> None:
        """Handle this message to me..."""
        self.logger.debug("server handling msg...")
        if msg.msg == CommonMSG.MSG_WC_STOCK_CHECK:
            # the server is sending a list of all stock locations
            # in response to a MSG_WC_STOCK_CHECK
            self.timerTM.set_active(False)
            wc_stock_dct = self.stockdb.generate_webclient_stocklist()
            self.send_WS_msg(CommonMSG(CommonMSG.MSG_SV_NEW_STOCK_LIST, wc_stock_dct))
        elif msg.msg == CommonMSG.MSG_WC_RADAR_MODE:
            self.logger.debug("server in RADAR mode...")
            self.timerTM.set_active(True)
        elif msg.msg == CommonMSG.MSG_SV_TIMER_TICK:
            self.logger.debug("server received tick...")
            # print("MY logger is called '{}'".format(get_logger_name(self.logger)))
            if self.tls.is_in_radarmode():
                self.tls.RadarGet()
        elif msg.msg == CommonMSG.MSG_WC_LOGIN_TRY:
            self.logger.debug("server received LOGIN request...")
            # try to log in and send back the response
            un = msg.data.get('username', None)
            pw = msg.data.get('password', None)
            login_resp = self.qaisession.login_try(self.qai_url, un, pw)
            # self.sleep(3)
            if not isinstance(login_resp, dict):
                raise RuntimeError("fatal login try error")
            self.send_WS_msg(CommonMSG(CommonMSG.MSG_SV_LOGIN_RES, login_resp))
            # dict(ok=False, msg="User unknown", data=msg.data)))
        elif msg.msg == CommonMSG.MSG_WC_LOGOUT_TRY:
            # log out and send back response.
            self.qaisession.logout()
            log_state = self.qaisession.is_logged_in()
            self.send_WS_msg(CommonMSG(CommonMSG.MSG_SV_LOGOUT_RES,
                                       dict(logstate=log_state)))
        elif msg.msg == CommonMSG.MSG_WC_QAI_AUTH:
            self.logger.debug("server received auth info...")
            cookie = msg.data
            self.logger.debug("server got cookie {}...".format(cookie))
        else:
            self.logger.error("server not handling message {}".format(msg))
            raise RuntimeError("unhandled message")

    def mainloop(self, ws: websocket):
        """This routine is entered into when the webclient has established a
        websocket connection to the server.
        """
        self.ws = ws
        # start a random generator thread for testing....
        # self.randTM = Taskmeister.RandomGenerator(self.msgQ, self.logger)
        # self.randTM.set_active(True)

        if self.ws is not None:
            # create a websocket reader thread
            self.websocketTM = Taskmeister.WebSocketReader(self.msgQ, self.logger, self.ws)

        # sent the RFID status to the webclient
        is_up = self.cl.is_alive()
        self.send_WS_msg(CommonMSG(CommonMSG.MSG_SV_RFID_STATREP, is_up))

        rfid_act_on = CommonMSG(CommonMSG.MSG_SV_RFID_ACTIVITY, True)
        rfid_act_off = CommonMSG(CommonMSG.MSG_SV_RFID_ACTIVITY, False)
        # set up the RFID activity delay timer
        self.rfid_delay_task = Taskmeister.DelayTaskMeister(self.msgQ,
                                                            self.logger,
                                                            1.5,
                                                            rfid_act_off)
        while True:
            msg: CommonMSG = self.msgQ.get()
            self.logger.debug("handling msgtype '{}'".format(msg.msg))
            if msg.is_from_rfid_reader():
                self.logger.debug("GOT RFID {}".format(msg.as_dict()))
                self.send_WS_msg(rfid_act_on)
                self.rfid_delay_task.trigger()

            is_handled = False
            if self.ws is not None and msg.msg in serverclass.MSG_FOR_WC_SET:
                is_handled = True
                self.send_WS_msg(msg)
            if msg.msg in serverclass.MSG_FOR_RFID_SET:
                is_handled = True
                self.tls.send_RFID_msg(msg)
            if msg.msg in serverclass.MSG_FOR_ME_SET:
                is_handled = True
                self.server_handle_msg(msg)
            if not is_handled:
                self.logger.error("mainloop DID NOT handle msgtype '{}'".format(msg.msg))
