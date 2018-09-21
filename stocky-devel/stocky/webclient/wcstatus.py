
import typing
import qailib.common.base as base


import qailib.transcryptlib.genutils as genutils
import qailib.transcryptlib.htmlelements as html
import qailib.transcryptlib.forms as forms
import qailib.transcryptlib.widgets as widgets
import qailib.transcryptlib.simpletable as simpletable

from commonmsg import CommonMSG


log = genutils.log

# May not import wccontroller or wcviews
# import wccontroller


STARATTR_ONCLICK = html.base_element.STARATTR_ONCLICK


class WCstatus(base.base_obj):
    """Visualise and store the webclient's bluetooth and logged-in status.
    Also store the stock information on the webclient that was sent
    from the stocky server.
    """
    NUM_ROW = 2
    NUM_COL = 3

    RFID_ROW = 0
    QAI_ROW = 1

    LED_COL = 0
    INFO_COL = 1
    QAI_UPD_COL = 2

    LOC_NOSEL_ID = "NOSEL_ID"
    LOC_NOSEL_NAME = "No Defined Location"

    def __init__(self, idstr: str,
                 mainprog: widgets.base_controller,
                 login_popup: forms.modaldiv) -> None:
        """Initialise the status bar (bluetooth and logged-in status)
        NOTE: mainprog is actually a "wccontroller.stocky_mainprog" instance, but
        because of javascript restrictions, cannot import that module here.
        We build everything into a predefined div called state-div.
        """
        super().__init__(idstr)
        self._stat_is_loggedin = False
        # empty stock information.. these are set in _setstockdata
        self._stockloc_lst: typing.List[dict] = []
        self._locid_item_dct: dict = {}
        self._ritemdct: dict = {}
        # empty locmut data..
        self.locmut_hash = "bla"
        self.locmut_dct = {}
        #
        self.mainprog = mainprog
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
        for title, rownum in [("RFID Scanner Status", WCstatus.RFID_ROW),
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
        # the login led is an opener for the login form
        login_popup.attach_opener(self.ledlst[WCstatus.QAI_ROW])

        # Set up the information for the QAI user name
        cell = mytab.getcell(WCstatus.QAI_ROW, WCstatus.INFO_COL)
        if cell is not None:
            txt = self.uname_text = html.spantext(cell,
                                                  "unametext",
                                                  {'class': "w3-tag w3-red",
                                                   "title": "Click here to log in to QAI"},
                                                  "not logged in")
            # the txt is opener for the login form
            login_popup.attach_opener(txt)
        else:
            log("cell table error 2")
            # self.uname_text = None
            return

        # install a general purpose busy spinner
        cell = mytab.getcell(WCstatus.RFID_ROW, WCstatus.QAI_UPD_COL)
        if cell is not None:
            spin_sz_pixels = 50
            spin_attrdct = {'title': "Server activity"}
            self.spinner = forms.spinner(cell, "busyspinner",
                                         spin_attrdct, forms.spinner.SPN_SPINNER,
                                         spin_sz_pixels)
        else:
            log("cell table error 2a")
            return
            
        # Set up the QAI last update tag
        cell = mytab.getcell(WCstatus.QAI_ROW, WCstatus.QAI_UPD_COL)
        if cell is not None:
            ustr = "The time of last QAI Stock list download. (log in and download stock list to update)"
            txt = self.qai_upd_text = html.spantext(cell,
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
                                            forms.spinner.SPN_COG, 20)
        else:
            # self.actspinner = None
            log("cell table error 3")
            return

    def set_login_response(self, resdct: dict) -> None:
        """Set the QAI logged in status according to resdct."""
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
            txt.setAttribute(STARATTR_ONCLICK, {'cmd': 'logout'})
            # the username text is NOT an opener for the login form
            self.login_popup.remove_opener(txt)
            txt.addObserver(self.mainprog, base.MSGD_BUTTON_CLICK)
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
            txt.remObserver(self.mainprog, base.MSGD_BUTTON_CLICK)

        txt.set_text(labtext)
        txt.setAttribute("title", txthelptext)

    def set_logout_status(self) -> None:
        """Set the visual status to 'logged out'"""
        self.set_login_response(dict(ok=False))

    def is_QAI_logged_in(self) -> bool:
        return self._stat_is_loggedin

    def set_RFID_state(self, on: bool) -> None:
        """Set the RFID LED state to on (green) or off (red)"""
        statusled = self.ledlst[WCstatus.RFID_ROW]
        if on:
            # set to green
            statusled.setcolour(html.LEDElement.GREEN)
        else:
            # set to red
            statusled.setcolour(html.LEDElement.RED)

    def set_busy(self, isbusy: bool) -> None:
        """Set the state of the 'busy' spinner"""
        self.spinner.set_spin(isbusy)

    def set_rfid_activity(self, on: bool) -> None:
        """Set the RFID spinner on/off """
        self.actspinner.set_spin(on)

    def set_QAIupdate_state(self, d: dict) -> None:
        """Set the string describing when the local DB was last
        updated from QAI"""
        upd_str = d['upd_time']
        print("UPDATE {}".format(upd_str))
        self.qai_upd_text.set_text(upd_str)
        stock_dct = d.get("stock_dct", None)
        if stock_dct is not None:
            self._setstockdata(stock_dct)
        else:
            print("RECEIVED EMPTY STOCK DATA")

    def _setstockdata(self, stockdct: dict) -> None:
        """Set the webclient's current  copy of the QAI chemicals stock DB.
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
        """Rge returned dict is taken directly from the ChemStock.Reagent_table
        and is of the form:
        {basetype: stockchem, catalog_number: TDF, category: Antiviral drugs/stds, date_msds_expires: null,
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
        # print("getregitems for loc: {}: {}".format(locid, retval))
        return retval

    def refresh_locmut_dct(self) -> None:
        """Request a new locmutation list from the stocky server
        if we need an update.
        This is done by sending a hash of the current data.
        The server will send an update if our data is out of date.
        """
        self.mainprog.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_LOCMUT_REQ, self.locmut_hash))

    def set_locmut_dct(self, dct: dict, newhash: str) -> None:
        """Set the location mutation dictionary"""
        print("NEW HASH {}".format(newhash))
        self.locmut_dct = dct
        self.locmut_hash = newhash
