
import typing
import qailib.common.base as base


import qailib.transcryptlib.genutils as genutils
# import qailib.common.serversocketbase as serversocketbase
import qailib.transcryptlib.htmlelements as html
import qailib.transcryptlib.forms as forms
import qailib.transcryptlib.widgets as widgets
# import qailib.transcryptlib.handlebars as handlebars
import qailib.transcryptlib.simpletable as simpletable

log = genutils.log

# May not import wccontroller or wcviews
# import wccontroller


STARATTR_ONCLICK = html.base_element.STARATTR_ONCLICK


class WCstatus(base.base_obj):
    """Visualise and store the webclient's bluetooth and logged-in status"""
    NUM_ROW = 2
    NUM_COL = 3

    RFID_ROW = 0
    QAI_ROW = 1

    LED_COL = 0
    INFO_COL = 1
    QAI_UPD_COL = 2

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
        self._stockloc_lst: typing.List[dict] = []
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
            log("cell table error 2a")
            # self.qai_upd_text = None
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

    def set_rfid_activity(self, on: bool) -> None:
        """set the RFID spinner on/off """
        self.actspinner.set_spin(on)

    def set_QAIupdate_state(self, d: dict) -> None:
        """Set the string describing when the local DB was last with from QAI"""
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
        """
        self._stockloc_lst = stockdct['loclst']
        # self._stockitm_lst = stockdct['itemlst']
        print(" SETTING LOCLIST LEN {}".format(len(self._stockloc_lst)))
        # self.preparechecklists()
        # self.showchecklist(0)

    def get_location_selector(self,
                              parent: html.base_element,
                              idstr: str,
                              helptext: str) -> html.select:
        """ Return a selector for the currently available list
        of locations."""
        selattrdct = {'title': helptext,
                      STARATTR_ONCLICK: {'cmd': 'locationswitch'},
                      "class": "w3-select locbutton-cls"}
        sel = html.select(parent, idstr, selattrdct, None)
        self.update_location_selector(sel)
        return sel

    def update_location_selector(self, sel: html.select) -> None:
        """Set the previously created select element to the current
        list of locations"""
        print(" LOCLIST LEN {}".format(len(self._stockloc_lst)))
        for locdct in self._stockloc_lst:
            name = locdct['name']
            idstr = locdct['id']
            sel.add_or_set_option(idstr, name)
