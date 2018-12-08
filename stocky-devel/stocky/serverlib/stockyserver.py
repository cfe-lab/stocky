import typing
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
                                CommonMSG.MSG_SV_RFID_STATREP,
                                CommonMSG.MSG_WC_LOGIN_TRY,
                                CommonMSG.MSG_WC_LOGOUT_TRY,
                                CommonMSG.MSG_WC_SET_STOCK_LOCATION,
                                CommonMSG.MSG_WC_LOCMUT_REQ,
                                CommonMSG.MSG_WC_ADD_STOCK_REQ,
                                CommonMSG.MSG_SV_TIMER_TICK,
                                CommonMSG.MSG_WC_LOCATION_INFO])

    def __init__(self, app: flask.Flask, CommLinkClass, cfgname: str) -> None:
        """

        Args:
           app: The flask app instance
           CommLinkClass: the name of the class to use for communicating\
              with the RFID reader (Commlink = serial communication link)
           cfgname: the name of the server configuration file (a YAML file)

        This class pull all of the data streams together and passes data
        between the actors. When first instantiated, this class performs
        the following.
          - a configuration file is read in
          - a message queue is instantiated
          - a connection to the RFID reader \
            (via a commlink instance passed to a TLSReader) is established.
          - a way of calling to the QAI API is established.
          - a local database of chemical stocks is opened.

        ..note::
           A connection to the webclient via websocket is *NOT* established
           at this stage; The Flask web framework passes a websocket instance to
           :meth:`mainloop` when the websocket makes a connection to the server.

        """
        # must set logging  before anything else...
        self._app = app
        self.logger = app.logger
        self.ws: typing.Optional[ServerWebSocket.BaseWebSocket] = None
        self.websocketTM: typing.Optional[Taskmeister.WebSocketReader] = None

        self.logger.info("serverclass: reading config file '{}'".format(cfgname))
        try:
            self.cfg_dct = serverconfig.read_server_config(cfgname)
        except RuntimeError as e:
            self.logger.error("Error reading server config file: {}".format(e))
            raise
        self.cfg_dct['logger'] = self.logger
        self.logger.debug("serverclass: config file read...{}".format(self.cfg_dct))
        timelib.set_local_timezone(self.cfg_dct['TZINFO'])
        self.name = "Johnny"
        self.msgQ = Queue()

        # start the rfcomm daemon...
        # the command to run is something along the lines of:
        # "/usr/bin/rfcomm connect /dev/rfcomm0 88:6B:0F:86:4D:F9"
        rfcomm_cmd = "{} connect {} {} ".format(self.cfg_dct['RFCOMM_PROGRAM'],
                                                self.cfg_dct['RFID_READER_DEVNAME'],
                                                self.cfg_dct['RFID_READER_BT_ADDRESS'])
        self.logger.debug("rfcomm command : '{}'".format(rfcomm_cmd))
        self.rfcommtask = Taskmeister.DaemonTaskMeister(self.logger,
                                                        rfcomm_cmd,
                                                        1)
        rfstat = self.rfcommtask.get_status()
        if rfstat != Taskmeister.DaemonTaskMeister.STATUS_RUNNING:
            self.logger.error("rfcomm daemon is not running: status = {}".format(rfstat))
            raise RuntimeError("rfcomm program has not started")
        self.logger.debug("rfcomm comand is running.")
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

        # create messages and a delayTM for the RFID activity spinner
        self._rfid_act_on = CommonMSG(CommonMSG.MSG_SV_RFID_ACTIVITY, True)
        rfid_act_off = CommonMSG(CommonMSG.MSG_SV_RFID_ACTIVITY, False)
        # set up the RFID activity delay timer
        self.rfid_delay_task = Taskmeister.DelayTaskMeister(self.msgQ,
                                                            self.logger,
                                                            1.5,
                                                            rfid_act_off)
        self.logger.info("End of serverclass.__init__")

    def send_WS_msg(self, msg: CommonMSG) -> None:
        """Send a command to the web client over websocket in a standard JSON format.

        Args:
           msg: the message to send.
        """
        if self.ws is not None:
            self.ws.sendMSG(msg.as_dict())

    def activate_RFID_spinner(self):
        """Send messages to the webclient in order to get the 'RFID activity' spinner
        to turn for a while.
        """
        self.send_WS_msg(self._rfid_act_on)
        self.rfid_delay_task.trigger()

    def sleep(self, secs: int) -> None:
        gevent.sleep(secs)

    def send_server_config(self) -> None:
        """Collect information about the server configuration and send this
        to the webclient.
        """
        # NOTE: the cfg_dct has keys we do not want to send to the webclient.
        dd = self.cfg_dct
        cfg_dct = dict([(k, dd[k]) for k in serverconfig.known_set])
        # extract information about the RFID reader if its online.
        rfid_info_dct = self.cl.get_info_dct()
        if rfid_info_dct is not None:
            for k, v in rfid_info_dct.items():
                cfg_dct[k] = v
        self.send_WS_msg(CommonMSG(CommonMSG.MSG_SV_SRV_CONFIG_DATA, cfg_dct))

    def BT_init_reader(self):
        """Initialise the RFID reader.
        This method should only be called when/if the RFID reader comes online.
        Raise an exception if this fails."""
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
        self.send_server_config()

    def server_handle_msg(self, msg: CommonMSG) -> None:
        """Handle this message to me, the stocky server

        Args:
           msg: the message to handle.
        """
        self.logger.debug("server handling msg...")
        print("server handling msg...{}".format(msg))
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
            print("server received LOGIN request...")
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
            print("chemstock 1 do_update={}".format(do_update))
            upd_dct: typing.Optional[dict] = None
            if do_update:
                upd_dct = self.stockdb.update_from_QAI()
                print("update dct {}".format(upd_dct))
            print("chemstock 2..")
            self.send_QAI_status(upd_dct)
            print("chemstock 3")
        elif msg.msg == CommonMSG.MSG_WC_ADD_STOCK_REQ:
            # get a string for adding RFID labels to QAI.
            dct = msg.data
            rfidstrlst = dct.get('rfids', None)
            locid = dct.get('location', None)
            new_stock = dct.get('newstock', False)
            qai_str = self.qaisession.generate_receive_url(locid, rfidstrlst, new_stock)
            self.send_WS_msg(CommonMSG(CommonMSG.MSG_SV_ADD_STOCK_RESP, qai_str))
        elif msg.msg == CommonMSG.MSG_SV_RFID_STATREP:
            print("state change enter")
            self.handleRFID_CLstatechange(msg.data)
            print("state change exit")
        elif msg.msg == CommonMSG.MSG_SV_FILE_STATE_CHANGE:
            print("state change enter")
            self.handleRFID_filestatechange(msg.data)
            print("state change exit")
        elif msg.msg == CommonMSG.MSG_WC_LOCATION_INFO:
            # location change information: save to DB
            self.stockdb.add_loc_changes(msg.data['locid'], msg.data['locdat'])
        elif msg.msg == CommonMSG.MSG_WC_LOCMUT_REQ:
            client_hash = msg.data
            newhash, rdct = self.stockdb.get_loc_changes(client_hash)
            if rdct is not None:
                self.send_WS_msg(CommonMSG(CommonMSG.MSG_SV_LOCMUT_RESP,
                                           dict(data=rdct, hash=newhash)))
        else:
            self.logger.error("server not handling message {}".format(msg))
            raise RuntimeError("unhandled message {}".format(msg))
        print("--END of server handling msg...{}".format(msg))

    def handleRFID_filestatechange(self, file_is_made: bool) -> None:
        """React to the serial device associated with the RFID reader appearing/disappearing.

        Args:
        Whether the serial device has been created/ deleted.
        """
        self.cl.HandleStateChange(file_is_made)

    def handleRFID_CLstatechange(self, new_state: int) -> None:
        """React to the serial device associated with the RFID reader appearing/disappearing.

        This routine is called whenever the BT connection to the RFID reader
        comes online/ comes offline or times out.
        Among other things, this routine calls :meth:`BT_init_reader` to ensure
        that the reader is in a defined state.

        Args:
           new_state: the new state of the serial communication link to the RFID reader.\
           This will be one of CommonMSG.RFID_ON, CommonMSG.RFID_OFF or CommonMSG.RFID_TIMEOUT.
        """
        self.logger.info("Commlink RFID state: {}".format(new_state))
        if new_state == CommonMSG.RFID_ON:
            print("Commlink is alive")
            print("serverclass: getting id_string...")
            idstr = self.cl.id_string()
            print("Commlink idents as '{}'".format(idstr))
            self.BT_init_reader()
            self.logger.info("Bluetooth init OK")
        elif new_state == CommonMSG.RFID_TIMEOUT:
            print("Restart RFCOMM")
            self.rfcommtask.stop_and_restart_cmd()

    def send_QAI_status(self, upd_dct: typing.Optional[dict]):
        if upd_dct is not None:
            did_dbreq = True
            dbreq_ok = upd_dct.get("ok", False)
            dbreq_msg = upd_dct.get("msg", "no message")
        else:
            did_dbreq = False
            dbreq_ok = True
            dbreq_msg = "NOTE: No update from QAI database performed."
        wc_stock_dct = self.stockdb.generate_webclient_stocklist()
        self.send_WS_msg(CommonMSG(CommonMSG.MSG_SV_STOCK_INFO_RESP,
                                   dict(db_stats=self.stockdb.get_db_stats(),
                                        upd_time=self.stockdb.get_update_time(),
                                        stock_dct=wc_stock_dct,
                                        did_dbreq=did_dbreq,
                                        dbreq_ok=dbreq_ok,
                                        dbreq_msg=dbreq_msg)))

    def mainloop(self, newws: ServerWebSocket.BaseWebSocket):
        """This routine is entered into when the webclient has established a
        websocket connection to the server.
        Flask will call this routine with a newly established web socket when
        the webclient makes a connection via the websocket protocol.

        Args:
           newws: the new websocket connection to the webclient.

        .. note::
           mainloop is reentrant: we enter here with a new websocket every time
           the webclient is started or restarted...

        The general strategy of the mainloop is to initialise all parties concerned,
        then enter an infinite loop in which messages are taken from the message queue.

        Messages are enqueued asynchronously from the various sources
        (webclient over websocket, RFID scanner over serial link) but the mainloop
        is the only entity dequeuing messages, and that happens in this loop.
        Some messages are either simply passed on to interested parties, while
        others are handled as requests by the server itself in
        :meth:`server_handle_msg` .
        """
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
        rfid_stat = self.cl.get_RFID_state()
        self.send_WS_msg(CommonMSG(CommonMSG.MSG_SV_RFID_STATREP, rfid_stat))
        # send the stocky server config data
        self.send_server_config()

        # send the QAI update status to the webclient
        self.send_QAI_status(None)

        do_loop = True
        while do_loop:
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
                do_loop = False
            print("step 2")
            if msg.is_from_rfid_reader():
                self.logger.debug("GOT RFID {}".format(msg.as_dict()))
                self.activate_RFID_spinner()

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
                print("msg for me: {}".format(msg.msg))
                is_handled = True
                self.server_handle_msg(msg)
                print("done handling")
            if not is_handled:
                mmm = "mainloop DID NOT handle msgtype '{}'".format(msg.msg)
                self.logger.error(mmm)
                print(mmm)
            print("end of ML.while")
        print("OUT OF LOOP")
