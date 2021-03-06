"""
Store and visualise the webclient status in the browser.
This modules keeps track of whether user is logged in, displays the
LED status buttons for server, RFID reader status etc.
"""


import typing
import qailib.common.base as base


import qailib.common.serversocketbase as serversocketbase
import qailib.transcryptlib.websocket as websocket
import qailib.transcryptlib.serversocket as serversock
import qailib.transcryptlib.genutils as genutils
import qailib.transcryptlib.htmlelements as html
import qailib.transcryptlib.forms as forms
import qailib.transcryptlib.simpletable as simpletable

from webclient.commonmsg import CommonMSG

RFID_ON = CommonMSG.RFID_ON
RFID_OFF = CommonMSG.RFID_OFF
RFID_TIMEOUT = CommonMSG.RFID_TIMEOUT


log = genutils.log

# NOTE: May not import wccontroller or wcviews


STARATTR_ONCLICK = html.base_element.STARATTR_ONCLICK

CMD_LOGOUT = 'logout'
CMD_TRY_RFID_SERVER = 'try_rfid_server'


class WCstatus(base.base_obj):
    """Visualise and store
       * the webclient's bluetooth status
       * logged-in status to QAIChangedct
       * the stocky webserver status over websocket.
    Also store the stock information on the webclient that was sent
    from the stocky server.
    """

    # the size of the spinners in pixels
    SPIN_SZ_PIXELS = 30

    NUM_ROW = 3
    NUM_COL = 2

    # SRV: status of comms to stocky server
    # RFID: status of RFID reader
    # QAI: whether logged in to QAI
    SRV_ROW = 0
    RFID_ROW = 1
    QAI_ROW = 2

    LED_COL = 0
    INFO_COL = 1
    # set this to INFO_COL..
    QAI_UPD_COL = 1

    LOC_NOSEL_ID = "NOSEL_ID"
    LOC_NOSEL_NAME = "No Defined Location"

    def __init__(self, idstr: str,
                 ws: serversocketbase.base_server_socket,
                 msg_listener: base.base_obj,
                 login_popup: forms.modaldiv) -> None:
        """Initialise the webclient status bar.

        Args:
           idstr: the instance's name
           ws: the websocket used for communication with the stocky server.
           msg_listener: the object that should receive messages from the RFID websocket.
           login_popup: the popup to be used to log a user in.
        Note:
           All visual HTML elements of this class are built into a
           predefined div in the DOM called state-div.
           If this div is missing in the DOM, then nothing is built.
        """
        super().__init__(idstr)
        self._rfid_ws: typing.Optional[serversock.JSONserver_socket] = None
        self._server_ws = ws
        self._msg_listener = msg_listener
        ws.addObserver(self, base.MSGD_COMMS_ARE_UP)
        ws.addObserver(self, base.MSGD_COMMS_ARE_DOWN)
        self._stat_is_loggedin = False
        self._stat_WS_isup = False
        # empty stock information.. these are set in _setstockdata
        self._stockloc_lst: typing.List[dict] = []
        self._locid_item_dct: dict = {}
        self._ritemdct: dict = {}
        # empty locmut data..
        self.locmut_hash = "bla"
        self.locmut_dct = {}
        self.srv_config_data: typing.Optional[typing.Dict[str, str]] = None
        #
        self.login_popup = login_popup
        self.statediv = statediv = html.getPyElementById("state-div")
        if statediv is None:
            log('STATE DIV MISSSING')
            return
        else:
            log("STATE DIV OK")
        tabattrdct: typing.Dict[str, str] = {}
        mytab = self.mytab = simpletable.simpletable(statediv, "statetable",
                                                     tabattrdct, WCstatus.NUM_ROW,
                                                     WCstatus.NUM_COL)

        self.ledlst: typing.List[html.LEDElement] = []
        for title, rownum in [("Stocky Server Status", WCstatus.SRV_ROW),
                              ("RFID Scanner Status", WCstatus.RFID_ROW),
                              ("Click to log in to QAI", WCstatus.QAI_ROW)]:
            ledattrdct = {"title": title}
            cell = mytab.getcell(rownum, WCstatus.LED_COL)
            if cell is not None:
                newled = html.LEDElement(cell,
                                         'statusled',
                                         ledattrdct,
                                         None,
                                         html.LEDElement.RED)
                self.ledlst.append(newled)
            else:
                log("cell table error 1")
                return
            #
            mytab.set_alignment(rownum, WCstatus.INFO_COL, "center")
        rfid_led = self.ledlst[WCstatus.RFID_ROW]
        rfid_led.setAttribute(STARATTR_ONCLICK, {'cmd': CMD_TRY_RFID_SERVER})
        rfid_led.addObserver(self, base.MSGD_BUTTON_CLICK)
        # the login led is an opener for the login form
        # login_popup.attach_opener(self.ledlst[WCstatus.QAI_ROW])

        # Set up the information for the QAI user name
        cell = mytab.getcell(WCstatus.QAI_ROW, WCstatus.INFO_COL)
        if cell is not None:
            self.uname_text = html.spantext(cell,
                                            "unametext",
                                            {'class': "w3-tag w3-red",
                                             "title": "Click here to log in to QAI"},
                                            "not logged in")
            # the txt is opener for the login form
            # login_popup.attach_opener(txt)
        else:
            log("cell table error 2")
            # self.uname_text = None
            return

        # install a general purpose busy spinner
        cell = mytab.getcell(WCstatus.SRV_ROW, WCstatus.QAI_UPD_COL)
        if cell is not None:
            spin_attrdct = {'title': "Server activity"}
            self.spinner = forms.spinner(cell, "busyspinner",
                                         spin_attrdct, forms.spinner.SPN_SPINNER,
                                         WCstatus.SPIN_SZ_PIXELS)
        else:
            log("cell table error 2a")
            return
        # Set up the QAI last update tag
        cell = mytab.getcell(WCstatus.QAI_ROW, WCstatus.QAI_UPD_COL)
        if cell is not None:
            ustr = "The time of last QAI Stock list download. (log in and download stock list to update)"
            self.qai_upd_text = html.spantext(cell,
                                              "unametext",
                                              {'class': "w3-tag w3-red",
                                               "title": ustr},
                                              "unknown")
        else:
            log("cell table error 2b")
            return

        # set up the RFID activity spinner
        cell = mytab.getcell(WCstatus.RFID_ROW, WCstatus.INFO_COL)
        if cell is not None:
            self.actspinner = forms.spinner(cell,
                                            "rfidspin",
                                            {"title": "RFID Scanner Activity"},
                                            forms.spinner.SPN_COG,
                                            WCstatus.SPIN_SZ_PIXELS)
        else:
            # self.actspinner = None
            log("cell table error 3")
            return

    def send_WS_msg(self, msg: CommonMSG) -> None:
        """Send a message to the server via websocket."""
        if self.is_WS_up():
            self._server_ws.send(msg.as_dict())
        else:
            print("SEND IS NOOOT HAPPENING")

    def set_login_response(self, resdct: dict) -> None:
        """Set the visual QAI logged in status according to resdct."""
        statusled = self.ledlst[WCstatus.QAI_ROW]
        self._stat_is_loggedin = is_logged_in = resdct['ok']
        in_col = "w3-green"
        out_col = "w3-red"
        txt = self.uname_text
        if is_logged_in:
            # success:
            uname = labtext = resdct.get('username', 'unknown')
            statusled.setcolour(html.LEDElement.GREEN)
            statusled.setAttribute("title", "Not '{}'? Click here to log in".format(uname))

            txthelptext = "Logged in to QAI. Click here to log out"
            txt.removeClass(out_col)
            txt.addClass(in_col)
            txt.setAttribute(STARATTR_ONCLICK, {'cmd': CMD_LOGOUT})
            # the username text is NOT an opener for the login form
            # self.login_popup.remove_opener(txt)
            txt.addObserver(self, base.MSGD_BUTTON_CLICK)
        else:
            # error:
            labtext = "not logged in"
            txthelptext = "Click here to log in to QAI"
            statusled.setcolour(html.LEDElement.RED)
            statusled.setAttribute("title", txthelptext)

            txt.removeClass(in_col)
            txt.addClass(out_col)
            txt.setAttribute(STARATTR_ONCLICK, dict(msg=forms.modaldiv._OPN_MSG))
            # the username text is an opener for the login form
            self.login_popup.attach_opener(txt)
            txt.remObserver(self, base.MSGD_BUTTON_CLICK)

        txt.set_text(labtext)
        txt.setAttribute("title", txthelptext)

    def set_logout_status(self) -> None:
        """Set the visual status to 'logged out'"""
        self.set_login_response(dict(ok=False))

    def is_QAI_logged_in(self) -> bool:
        """Query the logged in status.

        Returns:
           True iff the user is logged in to QAI.
        """
        return self._stat_is_loggedin

    def set_RFID_state(self, newstate: int) -> None:
        """Set the visual RFID LED state.
        The LED colour is set to on (green), off (red) or timeout (ORANGE).

        Args:
           newstate: this should be one of the predefined constants
              defined in CommonMSG (RFID_ON, RFID_OFF, RFID_TIMEOUT)
        """
        statusled = self.ledlst[WCstatus.RFID_ROW]
        if newstate == RFID_ON:
            # set to green
            statusled.setcolour(html.LEDElement.GREEN)
        elif newstate == RFID_OFF:
            # set to red
            statusled.setcolour(html.LEDElement.RED)
        elif newstate == RFID_TIMEOUT:
            statusled.setcolour(html.LEDElement.YELLOW)
        else:
            print("INVALID RFID LED STATE!")

    def set_busy(self, isbusy: bool) -> None:
        """Set the state of the 'internet is busy' spinner.

        Args:
           isbusy: True makes the spinner spin. False makes it stop.
        """
        self.spinner.set_spin(isbusy)

    def set_rfid_activity(self, on: bool) -> None:
        """Set the RFID spinner on/off

        Args:
           on: True makes the spinner spin. False makes it stop.
        """
        self.actspinner.set_spin(on)

    def set_WS_state(self, is_up: bool) -> None:
        """Set the colour of the LED indicating websocket communication to the stocky server.

        Args:
           is_up: True if the server is up (green light displayed). False to down (red light displayed).
        """
        print("WC status : {}".format(is_up))
        statusled = self.ledlst[WCstatus.SRV_ROW]
        self._stat_WS_isup = is_up
        if is_up:
            # set to green
            statusled.setcolour(html.LEDElement.GREEN)
        else:
            # set to red
            statusled.setcolour(html.LEDElement.RED)
        self._enable_login_popup(is_up)

    def _enable_login_popup(self, do_enable: bool) -> None:
        """Enable or disable the login popup.

        Args:
           do_enable: True will enable the QAI login popup.

        Note:
           The popup should be disabled if the websocket comms are down, as its
        the stocky server that will ultimately communicate with the QAI server.
        """
        login_popup = self.login_popup
        txt = self.uname_text
        if do_enable:
            # the login led is an opener for the login form
            login_popup.attach_opener(self.ledlst[WCstatus.QAI_ROW])
            if self.is_QAI_logged_in():
                # the username text is NOT an opener for the login form
                login_popup.remove_opener(txt)
            else:
                # if we are NOT logged in to QAI already,
                # the txt is opener for the login form
                login_popup.attach_opener(txt)
        else:
            login_popup.remove_opener(self.ledlst[WCstatus.QAI_ROW])
            login_popup.remove_opener(txt)

    def is_WS_up(self) -> bool:
        """Return the status of the websocket communication to the stocky server.

        Returns:
           True iff communication to the stocky server is up.
        """
        return self._stat_WS_isup

    def rcvMsg(self, whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]) -> None:
        lverb = True
        if lverb:
            # print("{}.rcvMsg: {}: {} from {}".format(self._idstr, msgdesc, msgdat, whofrom._idstr))
            print("{}.rcvMsg: {} from {}".format(self._idstr, msgdesc, whofrom._idstr))
        if msgdesc == base.MSGD_BUTTON_CLICK:
            print("wcstatus GOT BUTTON CLICK msgdat={}".format(msgdat))
            if msgdat is None:
                print("msgdat is None")
                return
            cmd = msgdat.get("cmd", None)
            print("wcstatus GOT BUTTON CLICK CMD {}".format(cmd))
            if cmd == CMD_LOGOUT:
                # the logout button was pressed
                self.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_LOGOUT_TRY, 1))
            elif cmd == CMD_TRY_RFID_SERVER:
                self._check_for_RFID_server()
            else:
                print('wcstatus: unrecognised cmd {}'.format(cmd))
                return
        elif msgdesc == base.MSGD_COMMS_ARE_UP:
            # this happens when the stocky server or RFID server websocket first comes online.
            # Use it for setting status and some initial data caching.
            print("COMMS ARE UP: {}".format(whofrom))
            if whofrom == self._server_ws:
                self.set_WS_state(True)
                self.refresh_locmut_dct()
            elif whofrom == self._rfid_ws:
                print("MSG FROM RFID server!!")
        elif msgdesc == base.MSGD_COMMS_ARE_DOWN:
            # this happens when the stocky server crashes, taking
            # the websocket connection with it
            print("COMMS ARE DOWN: {}".format(whofrom))
            if whofrom == self._server_ws:
                self.set_WS_state(False)
            elif whofrom == self._rfid_ws:
                self._rfid_ws = None
                self.set_RFID_state(RFID_OFF)

    def set_QAIupdate_state(self, d: dict) -> None:
        """Set the data state from the stocky server. This includes
        the whole chemical stock database.
        It also includes the string describing when the local DB was last
        updated from QAI.
        """
        upd_str = d['upd_time']
        did_dbreq = d.get("did_dbreq", False)
        dbreq_ok = d.get("dbreq_ok", False)
        dbreq_msg = d.get("dbreq_msg", "")
        print("UPDATE {}, did_dbreq: {}, dbreq_ok: {}, dbreq_msg; {}".format(upd_str,
                                                                             did_dbreq,
                                                                             dbreq_ok,
                                                                             dbreq_msg))
        self.qai_upd_text.set_text(upd_str)
        stock_dct = d.get("stock_dct", None)
        if stock_dct is not None:
            self._setstockdata(stock_dct)
        else:
            print("RECEIVED EMPTY STOCK DATA")

    def _setstockdata(self, stockdct: dict) -> None:
        r"""Set the webclient's current  copy of the QAI chemicals stock DB.
        NOTE: the loclist is a list of dict with id, and name entries:
        {'id': 10031, 'name': 'SPH\604\Research Fridge'},
        {'id': 10032, 'name': 'SPH\638\Freezer 6'}

        NOTE: the stockdct dictionary is built on the server side in
        ChemStock.DOgenerate_webclient_stocklist() .
        The keys we use here must obviously match those used there.
        """
        self._stockloc_lst = stockdct['loclst']
        # self._stockitm_lst = stockdct['itemlst']
        print(" SETTING LOCLIST LEN {}".format(len(self._stockloc_lst)))
        self._locid_item_dct = stockdct['locdct']
        print(" SETTING LOCITEMDCT LEN {}".format(len(self._locid_item_dct)))
        self._ritemdct = stockdct['ritemdct']
        self._reagentdct = stockdct['reagentdct']
        print(" SETTING REAGENTDCT LEN {}".format(len(self._reagentdct)))
        # self.preparechecklists()
        # self.showchecklist(0)

    def get_location_selector(self,
                              parent: html.base_element,
                              idstr: str,
                              helptext: str,
                              add_nosel: bool) -> html.select:
        """Return an html.select element for the currently available list
        of locations."""
        selattrdct = {'title': helptext,
                      STARATTR_ONCLICK: {'cmd': 'locationswitch'},
                      "class": "w3-select locbutton-cls"}
        sel = html.select(parent, idstr, selattrdct, None)
        self.update_location_selector(sel, add_nosel)
        return sel

    def update_location_selector(self,
                                 sel: html.select, add_nosel: bool) -> None:
        """Set the previously created select element to the current
        list of locations"""
        print("LOCLIST LEN {}".format(len(self._stockloc_lst)))
        for locdct in self._stockloc_lst:
            name = locdct['name']
            idstr = locdct['id']
            sel.add_or_set_option(idstr, name)
        if add_nosel:
            sel.add_or_set_option(WCstatus.LOC_NOSEL_ID, WCstatus.LOC_NOSEL_NAME)

    def get_reagent_info(self, rid: str) -> typing.Optional[dict]:
        """The returned dict is taken directly from the ChemStock.Reagent_table
        and is of the form:
        {basetype: stockchem, catalog_number: TDF, category: Antiviral drugs/stds,
         date_msds_expires: null,
         disposed: t, expiry_time: 2555, hazards: null, id: 6371, location: 605 dessicator,
         msds_filename: null, name: Tenofovir Tablet, needs_validation: null, notes: null,
         qcs_document_id: null, storage: Room Temperature, supplier: Pharmacy}

        """
        return self._reagentdct.get(rid, None)

    def get_location_items(self, locid: str) -> typing.Optional[list]:
        """Return the list of all reagent items that have been registered as
        being at this location.
        """
        retval = self._locid_item_dct.get(locid, None)
        retval = retval[1] if retval else None
        print("getregitems for loc: {}: {}".format(locid, retval))
        return retval

    def refresh_locmut_dct(self) -> None:
        """Request a new locmutation list from the stocky server
        if we need an update.
        This is done by sending a hash of the current data.
        The server will send an update if our data is out of date.
        """
        self.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_LOCMUT_REQ, self.locmut_hash))

    def set_locmut_dct(self, newdct: dict, newhash: str) -> None:
        """Set the location mutation dictionary.
        If the data has changed from a previous server poll, this will generate a
        MSGD_ON_CHANGE message.
        """
        print("NEW locmut HASH {}".format(newhash))
        print("NEW locmut dct {}".format(newdct))
        self.locmut_dct = newdct
        oldhash = self.locmut_hash
        self.locmut_hash = newhash
        if oldhash != newhash:
            msgdat = dict(msg='locmutdata')
            self.sndMsg(base.MSGD_ON_CHANGE, msgdat)

    def get_locmut_dct(self) -> dict:
        """Return the current location mutation dictionary.
        """
        return self.locmut_dct

    def get_stockloc_dct(self) -> typing.Dict[int, str]:
        """Return a dict locid : loc name.
        NOTE: self._stockloc_lst is a list of dicts... we undo this here
        """
        return dict([(locdct['id'], locdct['name']) for locdct in self._stockloc_lst])

    def get_reagent_item_dct(self) -> dict:
        """Return a dict of reagent items. The key is the reagent item id,
        and the value is a dict of the form
        {'id': 17713, 'last_seen': {},
          'lot_num': '705274',
        'notes': 'For MS Vacuum Pump - no expiry designated on product, just made up a date.',
        'qcs_location_id': 10032, 'qcs_reag_id': 8726,
        'rfid': '(no RFID)'
        }
        """
        # NOTE: can't seem to get nested list comprehensions to work in transcrypt..
        ll = []
        for list_list in self._ritemdct.values():
            ll.extend([(ri['id'], ri) for ri in list_list])
        return dict(ll)

    def set_server_cfg_data(self, new_cfg: dict) -> None:
        """This method is called in order to set stocky server configuration data
        to wcstatus.

        Args:
           new_cfg: a dict containing the stocky server configuration.
        """
        self.srv_config_data = new_cfg
        self._check_for_RFID_server()

    def get_server_cfg_data(self) -> typing.Optional[dict]:
        return self.srv_config_data

    def _check_for_RFID_server(self) -> None:
        print("check_for_RFID_server !!")
        urlstr = self.srv_config_data['RFID_SERVER_IP'] + '/goo'
        print("RFID URLSTR is '{}'".format(urlstr))
        if self._rfid_ws is None:
            rawsock = websocket.RawWebsocket(urlstr, ['/'])
            ws = serversock.JSONserver_socket('rfidsock', rawsock)
            ws.addObserver(self, base.MSGD_COMMS_ARE_UP)
            ws.addObserver(self, base.MSGD_COMMS_ARE_DOWN)
            ws.addObserver(self._msg_listener, base.MSGD_SERVER_MSG)
            self._rfid_ws = ws
        else:
            print("RFID socket already open")
