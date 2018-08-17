# import typing
import flask

import gevent
from gevent.queue import Queue

import serverlib.ServerWebSocket as ServerWebSocket
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
                                # CommonMSG.MSG_RF_STOCK_DATA,
                                CommonMSG.MSG_RF_RADAR_DATA,
                                CommonMSG.MSG_RF_CMD_RESP,
                                CommonMSG.MSG_SV_RFID_STATREP,
                                CommonMSG.MSG_SV_RFID_ACTIVITY])

    # the set of messages to send to the TLS class (the RFID reader)
    MSG_FOR_RFID_SET = frozenset([CommonMSG.MSG_SV_GENERIC_COMMAND,
                                  CommonMSG.MSG_WC_RADAR_MODE])

    # the set of messages the server should handle itself.
    MSG_FOR_ME_SET = frozenset([CommonMSG.MSG_WC_RADAR_MODE,
                                CommonMSG.MSG_WC_STOCK_INFO_REQ,
                                CommonMSG.MSG_SV_FILE_STATE_CHANGE,
                                CommonMSG.MSG_WC_LOGIN_TRY,
                                CommonMSG.MSG_WC_LOGOUT_TRY,
                                CommonMSG.MSG_WC_SET_STOCK_LOCATION,
                                CommonMSG.MSG_WC_ADD_STOCK_REQ,
                                CommonMSG.MSG_SV_TIMER_TICK])

    def __init__(self, app: flask.Flask, CommLinkClass, cfgname: str) -> None:
        # must set logging  before anything else...
        self._app = app
        self.logger = app.logger
        self.ws = None
        self.websocketTM = None

        self.logger.info("serverclass: reading config file '{}'".format(cfgname))
        self.cfg_dct = serverconfig.read_server_config(cfgname)
        self.cfg_dct['logger'] = self.logger
        self.logger.debug("serverclass: config file read...{}".format(self.cfg_dct))
        timelib.set_local_timezone(self.cfg_dct['TZINFO'])
        self.name = "Johnny"
        self.msgQ = Queue()
        self.logger.debug("serverclass: instantiating CommLinkClass...")
        self.filewatcher = Taskmeister.FileChecker(self.msgQ, self.logger, 5, True,
                                                   self.cfg_dct['RFID_READER_DEVNAME'])
        self.cl = CommLinkClass(self.cfg_dct)
        self.logger.debug("serverclass: instantiating TLSAscii...")
        self.tls = TLSAscii.TLSReader(self.msgQ, self.logger, self.cl, AVENUM)
        # now: set up our channel to QAI
        qai_url = self.cfg_dct['QAI_URL']
        self.qai_file = self.cfg_dct['LOCAL_STOCK_DB_FILE']
        self.logger.info("QAI info URL: '{}', file: '{}'".format(qai_url, self.qai_file))
        self.qaisession = qai_helper.QAISession(qai_url)
        self.logger.info("Instantiating ChemStock")
        self.stockdb = ChemStock.ChemStockDB(self.qai_file,
                                             self.qaisession,
                                             self.cfg_dct['TIME_ZONE'])
        # now: get our current stock list from QAI

        # create a timer tick for use in radar mode
        self.logger.info("Instantiating Tickgenerator")
        self.timerTM = Taskmeister.TickGenerator(self.msgQ, self.logger, 1, 'radartick')
        self.timerTM.set_active(False)
        self.logger.info("End of serverclass.__init__")

    def send_WS_msg(self, msg: CommonMSG) -> None:
        """Send a command to the web client over websocket in a standard JSON format."""
        if self.ws is not None:
            self.ws.sendMSG(msg.as_dict())

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
        self.tls.BT_set_stock_check_mode()

    def server_handle_msg(self, msg: CommonMSG) -> None:
        """Handle this message to me..."""
        self.logger.debug("server handling msg...")
        print("server handling msg...")
        if msg.msg == CommonMSG.MSG_WC_RADAR_MODE:
            radar_on = msg.data
            self.logger.debug("RADAR mode...{}".format(radar_on))
            self.timerTM.set_active(radar_on)
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
            if un is None or pw is None:
                self.logger.debug("server received a None with LOGIN request...")
            else:
                self.logger.debug("LOGIN request data OK...")
            print("trying login")
            login_resp = self.qaisession.login_try(un, pw)
            print("got login resp")
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
        elif msg.msg == CommonMSG.MSG_WC_STOCK_INFO_REQ:
            # request about chemstock information
            do_update = msg.data.get('do_update', False)
            print("chemstock 1 {}".format(do_update))
            if do_update:
                self.stockdb.update_from_QAI()
            print("chemstock 2..")
            self.send_QAI_status()
            print("chemstock 3")
        elif msg.msg == CommonMSG.MSG_WC_ADD_STOCK_REQ:
            # get a string for adding RFID labels to QAI.
            dct = msg.data
            rfidstrlst = dct.get('rfids', None)
            locid = dct.get('location', None)
            qai_str = self.qaisession.generate_receive_url(locid, rfidstrlst)
            self.send_WS_msg(CommonMSG(CommonMSG.MSG_SV_ADD_STOCK_RESP, qai_str))
        elif msg.msg == CommonMSG.MSG_SV_FILE_STATE_CHANGE:
            self.handleRFIDstatechange(msg.data)
        else:
            self.logger.error("server not handling message {}".format(msg))
            raise RuntimeError("unhandled message {}".format(msg))

    def handleRFIDstatechange(self, is_online: bool) -> None:
        """This routine is called whenever the BT connection to the RFID reader
        comes online/ comes offline.
        """
        commlink = self.cl
        commlink.HandleStateChange(is_online)
        rfid_is_alive = commlink.is_alive()
        if rfid_is_alive:
            self.logger.debug("Commlink is alive")
            self.logger.debug("serverclass: getting id_string...")
            idstr = self.cl.id_string()
            self.logger.info("Commlink idents as '{}'".format(idstr))
            self.BT_init_reader()
            self.logger.info("Bluetooth init OK")
        else:
            self.logger.info("Commlink is NOT alive...")
            self.logger.info("Skipping Bluetooth init...")
        # now tell the webclient...
        self.send_WS_msg(CommonMSG(CommonMSG.MSG_SV_RFID_STATREP, is_online))

    def send_QAI_status(self):
        wc_stock_dct = self.stockdb.generate_webclient_stocklist()
        self.send_WS_msg(CommonMSG(CommonMSG.MSG_SV_STOCK_INFO_RESP,
                                   dict(db_stats=self.stockdb.get_db_stats(),
                                        upd_time=self.stockdb.get_update_time(),
                                        stock_dct=wc_stock_dct)))

    def mainloop(self, newws: ServerWebSocket.BaseWebSocket):
        """This routine is entered into when the webclient has established a
        websocket connection to the server.
        """
        # NOTE: mainloop is reentrant: we enter here with a new websocket every time
        # the webclient is started or restarted...
        lverb = True
        print("mainloop with {}".format(newws))
        if self.ws is not None:
            # close the old websocket first.
            self.ws.close()
            self.ws = None
        self.ws = newws
        # start a random generator thread for testing....
        # self.randTM = Taskmeister.RandomGenerator(self.msgQ, self.logger)
        # self.randTM.set_active(True)

        # create a websocket reader thread
        self.websocketTM = Taskmeister.WebSocketReader(self.msgQ, self.logger, self.ws)

        # send the RFID status to the webclient
        is_up = self.cl.is_alive()
        self.send_WS_msg(CommonMSG(CommonMSG.MSG_SV_RFID_STATREP, is_up))

        # send the QAI update status to the webclient
        self.send_QAI_status()

        rfid_act_on = CommonMSG(CommonMSG.MSG_SV_RFID_ACTIVITY, True)
        rfid_act_off = CommonMSG(CommonMSG.MSG_SV_RFID_ACTIVITY, False)
        # set up the RFID activity delay timer
        self.rfid_delay_task = Taskmeister.DelayTaskMeister(self.msgQ,
                                                            self.logger,
                                                            1.5,
                                                            rfid_act_off)
        while True:
            if lverb:
                print("YO: before get")
            msg: CommonMSG = self.msgQ.get()
            self.logger.debug("handling msgtype '{}'".format(msg.msg))
            if lverb:
                print("YO: handling msgtype '{}'".format(msg.msg))
            # handle a EOF separately
            if msg.msg == CommonMSG.MSG_WC_EOF:
                if lverb:
                    print("mainloop detected WS_EOF... quitting")
                self.ws = None
                return
            if msg.is_from_rfid_reader():
                self.logger.debug("GOT RFID {}".format(msg.as_dict()))
                self.send_WS_msg(rfid_act_on)
                self.rfid_delay_task.trigger()

            is_handled = False
            if self.ws is not None and msg.msg in serverclass.MSG_FOR_WC_SET:
                is_handled = True
                # print("sending to WS...")
                self.send_WS_msg(msg)
                # print("...OK send")
            if msg.msg in serverclass.MSG_FOR_RFID_SET:
                is_handled = True
                self.tls.send_RFID_msg(msg)
            if msg.msg in serverclass.MSG_FOR_ME_SET:
                is_handled = True
                self.server_handle_msg(msg)

            if not is_handled:
                mmm = "mainloop DID NOT handle msgtype '{}'".format(msg.msg)
                self.logger.error(mmm)
                # print(mmm)
            # print("end of ML.while")
