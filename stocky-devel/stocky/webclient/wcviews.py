"""This module defines specific views for the webclient """

import typing
from org.transcrypt.stubs.browser import window
import qailib.common.base as base

import qailib.transcryptlib.htmlelements as html
import qailib.transcryptlib.simpletable as simpletable
import qailib.transcryptlib.widgets as widgets
import qailib.transcryptlib.cleverlabels as cleverlabels
import qailib.transcryptlib.SVGlib as SVGlib

# NOTE: would like to import this here for typing, but it leads to javascript
# run time errors because the modules import each other)
# import wccontroller

from webclient.commonmsg import CommonMSG
import webclient.wcstatus as wcstatus

BIG_DISTANCE = 99.0

STARATTR_ONCLICK = html.base_element.STARATTR_ONCLICK

LOC_NOSEL_ID = wcstatus.WCstatus.LOC_NOSEL_ID

button_classes = 'w3-button w3-border sco-push-click'


class SwitcheeView(widgets.BasicView):
    def __init__(self, contr: widgets.base_controller,
                 parent: widgets.base_widget,
                 idstr: str,
                 attrdct: dict,
                 jsel,
                 titletext: str,
                 helptext: str) -> None:
        """A base class for all other views in this module.

        Args:
           contr: the webclient controller
           parent: the parent in the visible HTML DOM hierarchy
           idstr: the instance's id string
           attrdct: the HTML attribute dict
           jsel: the optional javascript element
           titletext: text to be used as a title of the view. It will be displayed as\
              a H1 html element.
           helptext: further explanation of the view's purpose.
        """
        super().__init__(contr, parent, idstr, attrdct, jsel)
        self.wcstatus: wcstatus.WCstatus = contr.wcstatus
        self.addClass("w3-container")
        self.addClass('switchview-cls')
        self.setAttribute('height', '80%')
        self.setAttribute('width', '100%')
        self.h1 = html.h1text(self, titletext)
        help_attrdct = {'class': 'w3-container'}
        self.helptext = html.spanhelptext(self, "addhelptext", help_attrdct, helptext)

    def rcvMsg(self,
               whofrom: 'base.base_obj',
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]) -> None:
        if msgdesc == base.MSGD_BUTTON_CLICK:
            if msgdat is None:
                print("SwitcheeView: msgdat is None")
                return
            cmd = msgdat.get("cmd", None)
            # val = msgdat.get("target", None)
            # print("VIEW GOT {} {}".format(cmd, val))
            if cmd == "viewswitch":
                self.Redraw()

    def Redraw(self):
        """This method is called whenever the view becomes active (because the user
        has selected the respective view button.
        Subclasses should set up their pages in here.

        Note:
        This method could also be called in response to user input.
        Example: the user has chosen a different location, so we must redraw the page...
        """
        print("EMPTY VIEW REDRAW")


class RadarView(SwitcheeView):
    """The view to display when in Radar Mode. This will allow the user to search
       for a specific item"""
    def __init__(self, contr: widgets.base_controller,
                 parent: widgets.base_widget,
                 idstr: str,
                 attrdct: dict,
                 jsel) -> None:
        title_text = "Radar Mode"
        help_text = "Search for a specific RFID tag"
        SwitcheeView.__init__(self, contr, parent, idstr, attrdct, jsel,
                              title_text, help_text)
        size_tup = ('100%', '100%')
        # size_tup = None
        svg_attrdct = {'class': 'w3-container',
                       'width': '100%',
                       'height': '100%'}
        self.svg = SVGlib.svg(self, 'scosvg', svg_attrdct, None, size_tup)
        self.reset_radar()

    def reset_radar(self):
        """Clear the radar view """
        self.coldct = {}
        self.dist_lst = []

    def set_radardata(self, radarinfo: typing.List[typing.Tuple[str, int, float]]):
        """Display the radar data on the screen"""
        dist_lst = self.dist_lst
        coldct = self.coldct
        gotcols = {}
        for epc, ri, dist_val in radarinfo:
            numcol = len(dist_lst)
            colnum = coldct.get(epc, numcol)
            if colnum == numcol:
                print("newcol {}: epc, dst {} {}".format(colnum, epc, dist_val))
                dist_lst.append((epc, dist_val))
                coldct[epc] = colnum
            else:
                print("oldcol {}: epc, dst {} {}".format(colnum, epc, dist_val))
                dist_lst[colnum] = (epc, dist_val)
            gotcols[colnum] = True
        # -- set values those columns we did not in this list, to BIG_DISTANCE
        for epc, colnum in coldct.items():
            if gotcols.get(colnum, None) is None:
                print('setting col {} to bignum'.format(colnum))
                dist_lst[colnum] = (epc, BIG_DISTANCE)
        # now display the columns
        self.display_distances()

    def display_distances(self) -> None:
        """Display the distances in the columns"""
        self.svg.clear()
        for colnum, valtup in enumerate(self.dist_lst):
            epc, dist_val = valtup
            self.drawcolumn(colnum, epc, dist_val)

    def drawcolumn(self, colnum: int, epc: str, dst: float) -> None:
        """Draw a column representing the distance of this tag """
        svg = self.svg
        wscr, hscr = svg.get_WH()
        w_rect = 50
        colsep = 20
        w_column = w_rect + colsep

        xleft = colnum * w_column
        TOP_MARGIN = 20
        MAXH = hscr - TOP_MARGIN
        MAXDIST = 5.0
        h_rect = (dst*MAXH)/MAXDIST
        print("CALC dist {}, maxh {}, maxdist {} h_rect {} ".format(dst, MAXH, MAXDIST, h_rect))
        if h_rect > MAXH:
            h_rect = MAXH
        h_rect = int(h_rect)
        ytop = TOP_MARGIN + (MAXH - h_rect)
        print("DRAW {}: {} {} {} {}".format(colnum, xleft, ytop, w_rect, h_rect))
        red_colorstr = '#ff0066'
        blu_colorstr = '#6600ff'
        svg.rect(xleft, ytop, w_rect, h_rect, red_colorstr)
        svg.text(xleft, ytop, blu_colorstr, epc)


class BaseScanList:

    def add_scan(self, newdat: base.MSGdata_Type) -> None:
        """Add new RFID scan data to the list.
        The data is of the form:
        [['CS', '.iv'],
        ['EP', '000000000000000000001237'],
        ['RI', '-61'],
        ['EP', '000000000000000000001239'], ['RI', '-62'], ['EP', '000000000000000000001235']
        OR, in the case of barcode scan data:
        [['CS', '.bc'], ['BC', '000000000000000000001236'], ['OK', '']]

        We only add BC and EP fields, and also only if the tags begin with 'CHEM'
        """
        add_lst = [cont for tag, cont in newdat if (tag == 'EP' or tag == 'BC') and cont[:4] == 'CHEM']
        add_lst.sort()
        if len(add_lst) > 0:
            for cont in add_lst:
                self._register_RFID_token(cont)
            self.post_add_scan_CB()

    def _register_RFID_token(self, newtk: str) -> None:
        """This routine should be overridden in the subclasses"""
        print("BaseScanList: _register_RFID_token is being called. This is probably an error")

    def post_add_scan_CB(self) -> None:
        """This method is called whenever any new RFID labels have been added to the
        table. It can be overridden, e.g. to sort table rows
        """
        pass


class AddScanList(simpletable.simpletable, BaseScanList):
    """This class is used when adding new stock to the inventory or adding RFID tags
    to existing stock.
    It displays a list of RFID tags (left column) that have been scanned, and allows
    the user to choose whether they should be added or not (right column).
    """

    _RFID_COL = 0
    _ACTIV_COL = 1

    def __init__(self, parent: widgets.base_widget, idstr: str) -> None:
        attrdct: typing.Dict[str, str] = {'class': 'scanlist'}
        simpletable.simpletable.__init__(self, parent, idstr, attrdct, 0, 2)
        self.reset()

    def reset(self):
        """Empty any list in the table and ensure the column headers are in place..."""
        self._tkdct = {}
        self._sortdct = {}
        self.adjust_row_number(0)
        if not self.has_header_row():
            self.add_header_row()
            kattrdct = {'class': "w3-tag w3-blue"}
            for colnum, txt in [(AddScanList._RFID_COL, "RFID label"),
                                (AddScanList._ACTIV_COL, "Selected?")]:
                kcell = self.getheader(colnum)
                if kcell is not None:
                    html.label(kcell, "", kattrdct, txt, None)

    def _register_RFID_token(self, newtk: str) -> None:
        """This method is called when an RFID tag has been produced by
        the RFID reader. Handle it here.
        This method is overridden from BaseScanList.

        NOTE: here, we simply add any new token to the list if we haven't
        got it in the list already.
        """
        if newtk in self._tkdct:
            return
        on_attrdct = {'class': "w3-tag w3-green"}
        off_attrdct = {'class': "w3-tag w3-red"}
        on_text = "Add to QAI"
        off_text = "Ignore"
        # add the new token...
        rownum = self.append_row()
        kcell = self.getcell(rownum, AddScanList._RFID_COL)
        if kcell is not None:
            kattrdct = {'class': "w3-tag w3-border w3-purple"}
            html.label(kcell, "", kattrdct, newtk, None)
        vcell = self.getcell(rownum, AddScanList._ACTIV_COL)
        if vcell is not None:
            tog_lab = cleverlabels.DropToggleLabel(vcell, "rfid_lsb{}".format(rownum),
                                                   on_attrdct, on_text,
                                                   off_attrdct, off_text)
            self._tkdct[newtk] = tog_lab
        self.set_alignment(rownum, AddScanList._ACTIV_COL, "center")
        self._sortdct[newtk] = self._rowlst[rownum]

    def get_active_tags(self) -> typing.List[str]:
        """Return the list of RFID tags (in column 0) if the column 1
        state is OK.
        """
        return [k for k, tog in self._tkdct.items() if tog.is_A_state()]

    def post_add_scan_CB(self) -> None:
        """This method is called whenever any new RFID labels have been added to the
        table. Here, we sort the rows in ascending order of the RFID label.
        """
        # print("BEGIN SORTO !")
        sortlst = list(self._sortdct.items())
        sortlst.sort(key=lambda a: a[0])
        self._rowlst = [row for k, row in sortlst]
        self._reinsert_rows()
        # w3.sortHTML("scoaddscanlist", ".item", "td:nth-child(1)")
        print("END SORTO !")


class AddNewStockView(SwitcheeView):
    """This is the view that the user will use to add new stock to the QAI system
    or attach RFID labels to existing stock.
      * We allow the user to scan RFID tags and display them.
      * Once happy, the user hits one of two buttons and is redirected to a QAI window.
    """

    GO_RESET_TABLE = 'go_reste_table'
    GO_ADD_NEW_STOCK = 'go_add_new_stock'
    GO_ADD_NEW_RFIDTAG = 'go_add_new_rfidtag'

    def __init__(self, contr: widgets.base_controller,
                 parent: widgets.base_widget,
                 idstr: str,
                 attrdct: dict,
                 jsel) -> None:
        title_text = "Receiving: Add New Stock to QAI"
        help_text = """Use the scanner to enter RFID or barcode tags on chemical stock
items to be added to QAI for the first time."""
        SwitcheeView.__init__(self, contr, parent, idstr, attrdct, jsel,
                              title_text, help_text)
        print("AddNewStockView!!!")
        self.resetbutton: typing.Optional[html.textbutton] = None
        self.gobutton: typing.Optional[html.textbutton] = None
        self.tgbutton: typing.Optional[html.textbutton] = None
        self.scanlist: typing.Optional[AddScanList] = None
        contr.addObserver(self, base.MSGD_RFID_CLICK)

    def Redraw(self):
        """Build the view for adding new stock: present a table of scanned RFID labels.
        Allow user to modify this list, then add them to QAI when ready.
        """
        print("Add New stock REDRAW")
        # list of scanned RFID tags...
        if self.scanlist is None:
            self.scanlist = AddScanList(self, "scoaddscanlist")
        else:
            self.scanlist.reset()
        # now add a 'GO' button
        if self.resetbutton is None:
            idstr = "addloc-but1"
            attrdct = {'class': button_classes,
                       'title': "Remove all RFID labels from the table",
                       STARATTR_ONCLICK: dict(cmd=AddNewStockView.GO_RESET_TABLE)}
            buttontext = "Reset the table"
            self.resetbutton = html.textbutton(self, idstr, attrdct, buttontext)
            # NOTE: this class (NOT the controller) responds to this click...
            self.resetbutton.addObserver(self, base.MSGD_BUTTON_CLICK)
        if self.gobutton is None:
            idstr = "addloc-but2"
            attrdct = {'class': button_classes,
                       'title': "Add new stock items with RFID tags to QAI",
                       STARATTR_ONCLICK: dict(cmd=AddNewStockView.GO_ADD_NEW_STOCK)}
            buttontext = "Add new stock items to QAI"
            self.gobutton = html.textbutton(self, idstr, attrdct, buttontext)
            self.gobutton.addObserver(self._contr, base.MSGD_BUTTON_CLICK)
        if self.tgbutton is None:
            idstr = "addloc-but3"
            attrdct = {'class': button_classes,
                       'title': "Add RFID labels to existing stock items in QAI",
                       STARATTR_ONCLICK: dict(cmd=AddNewStockView.GO_ADD_NEW_RFIDTAG)}
            buttontext = "Add RFID labels to existing QAI items"
            self.tgbutton = html.textbutton(self, idstr, attrdct, buttontext)
            self.tgbutton.addObserver(self._contr, base.MSGD_BUTTON_CLICK)

    def rcvMsg(self,
               whofrom: 'base.base_obj',
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]) -> None:
        if msgdesc == base.MSGD_RFID_CLICK:
            print("GOT SCAN DATA {}".format(msgdat))
            if self.scanlist is not None and msgdat is not None:
                self.scanlist.add_scan(msgdat)
        elif msgdesc == base.MSGD_BUTTON_CLICK:
            if self.resetbutton is not None and whofrom == self.resetbutton:
                if self.scanlist is not None:
                    self.scanlist.reset()
            else:
                super().rcvMsg(whofrom, msgdesc, msgdat)
        else:
            super().rcvMsg(whofrom, msgdesc, msgdat)

    def get_selection_dct(self) -> typing.Optional[dict]:
        """Return the current selection on the page.
        This includes the location if any is selected and
        the list of actively selected RFID tags.
        Return None if no tags are currently selected.
        """
        if self.scanlist is None:
            return None
        add_rfid_lst = self.scanlist.get_active_tags()
        print("newstock {}".format(add_rfid_lst))
        if len(add_rfid_lst) == 0:
            return None
        # find the location selected...
        # NOTE: no longer user-defined location; instead must be configured (serverconfig)
        # just set this to None for now
        locid = None
        return {'rfids': add_rfid_lst, 'location': locid}

    def redirect(self, url: str) -> None:
        # this does indeed replace the current window
        # window.location = self.qai_url
        # this opens a new tab or window
        # if self.win is not None:
        #    self.win.close()
        # NOTE: If I give a name, e.g. "BLAWIN", then a tab is opened, and subsequently replaced --
        # just what I want. We call focus() on the window to switch the user's attention to
        # the new window.
        # NOTE: this is all native javascript...see
        # https://www.w3schools.com/jsref/met_win_open.asp
        newwin = window.open(url, "BLAWIN")
        newwin.focus()


# contr: wccontroller.stocky_mainprog,

class DownloadQAIView(SwitcheeView):
    """This is the view that the user will use to sync the stocky db with the QAI system.
      * check login status.
      *  if logged in:
            issue download order.
         else:
           tell user to log in.
    """
    def __init__(self,
                 contr: widgets.base_controller,
                 parent: widgets.base_widget,
                 idstr: str,
                 attrdct: dict,
                 jsel) -> None:
        title_text = "QAI Database Download Page"
        htext = """Update Stocky's Database from the QAI system.
For this to work, the stocky computer must be plugged in to ethernet and you must first log in."""
        SwitcheeView.__init__(self, contr, parent, idstr, attrdct, jsel,
                              title_text, htext)
        self.stat_tab: typing.Optional[simpletable.dict_table] = None
        self.message_bar: typing.Optional[html.alertbox] = None

    def Redraw(self):
        """Start the download if we are logged in."""
        is_logged_in = self.wcstatus.is_QAI_logged_in()
        print("LOGGED IN {}".format(is_logged_in))
        if is_logged_in:
            self._start_download()
        else:
            html.scoalert("Download only possible once logged in")

    def _start_download(self) -> None:
        # self.stat.set_text("Downloading QAI data...")
        self.wcstatus.set_busy(True)
        # typing.cast(wccontroller.stocky_mainprog, self._contr).start_QAI_download()
        self._contr.start_QAI_download()

    def stop_download(self, resdct: dict) -> None:
        """ This is called when the server tells us that the QAI download has completed."""
        # self.stat.set_text("Downloading successful...")
        did_dbreq = resdct.get("did_dbreq", False)
        dbreq_ok = resdct.get("dbreq_ok", False)
        dbreq_msg = resdct.get("dbreq_msg", "")
        tmp_dct = resdct.get('db_stats', None)
        print("ST stats 1 did_dbreq: {}, dbreq_ok: {}, dbreq_msg; {}".format(did_dbreq,
                                                                             dbreq_ok,
                                                                             dbreq_msg))
        print("SB stats 2 {}".format(tmp_dct))
        if self.message_bar is None:
            self.message_bar = html.alertbox(self, "alert-box", None, None)
        self.message_bar.set_text(dbreq_msg)

        db_stat_dct = dict(tmp_dct)
        if self.stat_tab is None:
            tab_attrdct = {'class': 'w3-container'}
            self.stat_tab = simpletable.dict_table(self, "stat_tab",
                                                   tab_attrdct,
                                                   list(db_stat_dct.items()))
        else:
            self.stat_tab.update_table(db_stat_dct)
        self.wcstatus.set_busy(False)


class rowtracker:
    """Keep track of all HTML elements on one row of a CheckScanList"""
    def __init__(self) -> None:
        pass


FSM_CLICK_EVENT = cleverlabels.FSMLabel.FSM_CLICK_EVENT
FSM_RFID_DETECT_EVENT = 'detected'


class CheckFSM(cleverlabels.SimpleFSM):
    ST_REPORT_FOUND = 0
    ST_REPORT_MISSING = 1
    ST_REPORT_MOVED = 2
    ST_IGNORE = 3
    ST_ERROR_STATE = 4

    def __init__(self, idstr: str,
                 isexpected: bool,
                 hasRFIDlabel: bool,
                 detected_lab: cleverlabels.ToggleLabel) -> None:
        self.isexpected = isexpected
        self.hasRFIDlabel = hasRFIDlabel
        self.isdetected_lab = detected_lab
        self.dd: dict = {}
        dd = self.dd
        # isexp, isdetect, curstate, --event -->  = newstate
        # expected items...
        dd[(True, False, CheckFSM.ST_REPORT_MISSING, FSM_CLICK_EVENT)] = CheckFSM.ST_IGNORE
        dd[(True, False, CheckFSM.ST_IGNORE, FSM_CLICK_EVENT)] = CheckFSM.ST_REPORT_MISSING
        #
        dd[(True, True, CheckFSM.ST_REPORT_MISSING, FSM_RFID_DETECT_EVENT)] = CheckFSM.ST_REPORT_FOUND
        dd[(True, True, CheckFSM.ST_IGNORE, FSM_RFID_DETECT_EVENT)] = CheckFSM.ST_REPORT_FOUND
        dd[(True, False, CheckFSM.ST_REPORT_FOUND, FSM_RFID_DETECT_EVENT)] = CheckFSM.ST_REPORT_MISSING
        # unexpected items...
        dd[(False, True, CheckFSM.ST_REPORT_MOVED, FSM_CLICK_EVENT)] = CheckFSM.ST_IGNORE
        dd[(False, True, CheckFSM.ST_IGNORE, FSM_CLICK_EVENT)] = CheckFSM.ST_REPORT_MOVED
        numstates = 5
        event_lst = [FSM_CLICK_EVENT, FSM_RFID_DETECT_EVENT]
        cleverlabels.SimpleFSM.__init__(self, idstr, numstates, event_lst)

    def get_init_state(self) -> int:
        """Return the initial state of the FSM."""
        if self.isexpected:
            if self.hasRFIDlabel:
                return CheckFSM.ST_REPORT_MISSING
            else:
                return CheckFSM.ST_IGNORE
        else:
            return CheckFSM.ST_ERROR_STATE

    def get_new_state(self, curstate: int, event: str) -> int:
        """Given the current state and an event that has
        occurred (information provided in self.os)
        determine the new_state"""
        isdetected = self.isdetected_lab.is_A_state()
        evtup = (self.isexpected, isdetected, curstate, event)
        newstate = self.dd.get(evtup, curstate)
        print("FSM transition {} : {}".format(evtup, newstate))
        return newstate


class CheckLabel(cleverlabels.FSMLabel):
    def __init__(self, parent: html.base_element,
                 idstr: str,
                 isexpected: bool,
                 has_rfid_label: bool,
                 detected_lab: cleverlabels.ToggleLabel) -> None:
        self.detected_lab = detected_lab
        myfsm = CheckFSM('checkfsm:{}'.format(idstr), isexpected, has_rfid_label, detected_lab)
        red_label = {'class': "w3-tag w3-red"}
        grn_label = {'class': "w3-tag w3-green"}
        org_label = {'class': "w3-tag w3-orange"}
        normal_label = {'class': "w3-tag"}
        at = {}
        at[CheckFSM.ST_REPORT_FOUND] = ('report as found', grn_label)
        at[CheckFSM.ST_REPORT_MISSING] = ('report as missing', red_label)
        at[CheckFSM.ST_REPORT_MOVED] = ('report as moved', org_label)
        at[CheckFSM.ST_IGNORE] = ('ignore', normal_label)
        at[CheckFSM.ST_ERROR_STATE] = ('ERROR state', red_label)
        #
        cleverlabels.FSMLabel.__init__(self, parent, idstr, myfsm, at)
        detected_lab.addObserver(self, base.MSGD_STATE_CHANGE)

    def rcvMsg(self,
               whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]) -> None:
        if whofrom == self.detected_lab:
            if msgdesc == base.MSGD_STATE_CHANGE:
                print('CheckLabel enter event 99')
                self.enter_event(FSM_RFID_DETECT_EVENT)


class CheckScanList(simpletable.simpletable, BaseScanList):
    """This class is used when adding new stock to the inventory.
    It displays a list of RFID tags (left column) that have been scanned,
    and allows the user to choose whether they should be added
    or not (right column).
    """

    _ITID_COL = 0
    _RFID_COL = 1
    _EXP_COL = 2
    _DESC_COL = 3
    _SCANSTAT_COL = 4
    _ACTION_COL = 5
    _NUM_COLS = 6

    def __init__(self,
                 parent: widgets.base_widget,
                 idstr: str,
                 wcstatus: wcstatus.WCstatus,
                 ll: typing.Optional[list],
                 rfid_sel_but: cleverlabels.SliderSwitch) -> None:
        attrdct: typing.Dict[str, str] = {'class': 'scanlist'}
        simpletable.simpletable.__init__(self, parent, idstr, attrdct, 0, CheckScanList._NUM_COLS)
        self.wcstatus = wcstatus
        self.rfid_sel_but = rfid_sel_but
        rfid_sel_but.addObserver(self, base.MSGD_ON_CHANGE)
        self.reset(ll)

    def rcvMsg(self,
               whofrom: 'base.base_obj',
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]) -> None:
        if msgdesc == base.MSGD_ON_CHANGE:
            rfid_itms_only = self.rfid_sel_but.get_checked()
            if rfid_itms_only:
                # set on/off depending on presence of rfid label
                for rtrack in self._row_dct.values():
                    self.setrowvisible(rtrack.rownum, rtrack.has_rfid_label)
            else:
                # set all rows on
                for rtrack in self._row_dct.values():
                    self.setrowvisible(rtrack.rownum, True)

    def reset(self, ll: typing.Optional[list]):
        """Empty any existing list in the table, then
        write a new table from the list of dicts...
        """
        print("checkscanlist.reset ll {}".format(ll))
        with html.ParentUncouple(self):
            self._rfid_dct = {}
            self._row_dct = {}
            if not self.has_header_row():
                # print("adding header...")
                self.add_header_row()
                kattrdct = {'class': "w3-tag w3-blue"}
                for colnum, txt in [(CheckScanList._ITID_COL, "Item ID"),
                                    (CheckScanList._RFID_COL, "RFID label"),
                                    (CheckScanList._EXP_COL, "Expected?"),
                                    (CheckScanList._DESC_COL, "Description"),
                                    (CheckScanList._SCANSTAT_COL, "Scan Status"),
                                    (CheckScanList._ACTION_COL, "Action")]:
                    kcell = self.getheader(colnum)
                    if kcell is not None:
                        html.label(kcell, "", kattrdct, txt, None)
            # -- add the elements from ll, all with an 'undetected' scan status.
            ll = ll or []
            self.adjust_row_number(len(ll))
            for rownum, rdct in enumerate(ll):
                self._add_expected_row(rownum, rdct)
        print("end reset ll")

    def _add_expected_row(self, rownum: int, rdct: dict) -> None:
        """We are given a dict:
        {'id': 17107, 'last_seen': {}, 'lot_num': 'MKBS0446V',
        'notes': 'for use of fridge/freezer probes',
        'qcs_location_id': 10046, 'qcs_reag_id': 8158, 'rfid': '(no RFID)'}
        here, add it to the table.

        NOTE: the table is expected to have the correct number of rows...just
        modify the cells on the give rownum here.
        """
        print("ADD_EXPECTED: {}".format(rdct))
        red_label = {'class': "w3-tag w3-red"}
        grn_label = {'class': "w3-tag w3-green"}
        normal_label = {'class': "w3-tag"}
        on_attrdct = grn_label
        off_attrdct = red_label
        # keep some salient information about the item in an rtracker object;
        # we keep a dict, _row_dct with the items's id as a key
        rtracker = rowtracker()
        # see whether we have a valid rfid token...
        has_rfid_label = rdct['rfid'].startswith('CHEM')
        rtracker.has_rfid_label = has_rfid_label
        if has_rfid_label:
            rfid_str = rdct['rfid']
            self._rfid_dct[rfid_str] = rtracker
        else:
            rfid_str = "none"
        rtracker.id = id_str = rdct['id']
        self._row_dct[id_str] = rtracker
        rtracker.expected = True
        rtracker.detected = False
        rtracker._dict = rdct
        rtracker.rownum = rownum

        # we retrieve the row to see whether we can reuse some of its columns...
        myrow = self.getrow(rownum)
        if myrow is None:
            print("row number {} is None".format(rownum))
            return
        is_new_row = myrow.isnew
        # print("exp row {} {}".format(rownum, is_new_row))

        # assemble description string
        reagent_id = rdct['qcs_reag_id']
        lotnum = rdct['lot_num']
        last_seen_str = rdct['last_seen'] or 'never'
        # last_seen_str = 'never'
        reag_dct = self.wcstatus.get_reagent_info(reagent_id)
        # put additional information about the reagent into a helptext that will be visible
        # by hovering the mouse over the description element.
        print("reag_dct is {}".format(reag_dct))
        if reag_dct is None:
            desc_str = "reagent id {} , lot: {}".format(reagent_id, lotnum)
            helptext = ""
        else:
            desc_str = "{}".format(reag_dct['name'])
            hazstr = reag_dct['hazards'] or "none"
            helptext = """basetype: {}, cat: {}, hazards: {},\
storage: {}, reagent_id: {}, last_seen: {}""".format(reag_dct['basetype'],
                                                     reag_dct['category'],
                                                     hazstr,
                                                     reag_dct['storage'],
                                                     reag_dct['id'],
                                                     last_seen_str)
        desc_attrdct = {'class': "w3-tag", 'title': helptext}
        for colnum, coltext, field_attrdct in [(CheckScanList._ITID_COL, id_str, normal_label),
                                               (CheckScanList._RFID_COL, rfid_str, normal_label),
                                               (CheckScanList._EXP_COL, 'expected', grn_label),
                                               (CheckScanList._DESC_COL, desc_str, desc_attrdct)]:
            if is_new_row:
                kcell = myrow.getcell(colnum)
                if kcell is not None:
                    lab = html.label(kcell, "", field_attrdct, coltext, None)
                    myrow.setcellcontent(colnum, lab)
                else:
                    print("error 99")
                    return
            else:
                lab = myrow.getcellcontent(colnum)
                # print("setty {}".format(lab))
                lab.set_text(coltext)
                if colnum == CheckScanList._DESC_COL:
                    lab.removeAttribute('title')
                    lab.setAttribute('title', helptext)
        # scan status
        if is_new_row:
            vcell = myrow.getcell(CheckScanList._SCANSTAT_COL)
            if vcell is not None:
                on_text = "detected"
                off_text = "undetected"
                scan_lab = cleverlabels.DropToggleLabel(vcell, "scanstat_tog{}".format(rownum),
                                                        on_attrdct, on_text,
                                                        off_attrdct, off_text)
                myrow.setcellcontent(CheckScanList._SCANSTAT_COL, scan_lab)
            self.set_alignment(rownum, CheckScanList._SCANSTAT_COL, "center")
        else:
            scan_lab = myrow.getcellcontent(CheckScanList._SCANSTAT_COL)
        scan_lab.set_state(False)
        rtracker.scanstat_tog = scan_lab
        # action column
        if is_new_row:
            vcell = myrow.getcell(CheckScanList._ACTION_COL)
            if vcell is not None:
                tog_lab = CheckLabel(vcell, "action_tog{}".format(rownum),
                                     True,
                                     has_rfid_label,
                                     scan_lab)
                myrow.setcellcontent(CheckScanList._ACTION_COL, tog_lab)
            self.set_alignment(rownum, CheckScanList._ACTION_COL, "center")
        else:
            tog_lab = myrow.getcellcontent(CheckScanList._ACTION_COL)
        tog_lab.reset_state()
        rtracker.action_tog = tog_lab
        myrow.isnew = False

    def _register_RFID_token(self, newtk: str) -> None:
        """This method is called when a RFID tag has been produced by
        the RFID reader. Handle it here.
        This method is overridden from BaseScanList.

        NOTE: here, a token might be expected or not for the current location.
        """
        if newtk in self._rfid_dct:
            print("newtk {} already in checkscanlist".format(newtk))
        else:
            self._add_unexpected(newtk)

    def _add_unexpected(self, newtk: str) -> None:
        """This method is called when an RFID tag is detected
        that is not expected for this location.
        """
        pass

    def get_move_list(self) -> typing.List[typing.Tuple[str, str]]:
        """Return the stock-taking action to perform on each row.
        """
        statedct = dict([(CheckFSM.ST_REPORT_FOUND, 'found'),
                         (CheckFSM.ST_REPORT_MISSING, 'missing'),
                         (CheckFSM.ST_REPORT_MOVED, 'moved'),
                         (CheckFSM.ST_IGNORE, 'ignore'),
                         (CheckFSM.ST_ERROR_STATE, 'errorstate')])
        retlst = []
        for row in self._rowlst:
            # id string
            txt = row.getcellcontent(CheckScanList._ITID_COL)
            idstr = txt.get_text()
            # action state
            action_label = row.getcellcontent(CheckScanList._ACTION_COL)
            action_int = action_label.get_current_state()
            if action_int != CheckFSM.ST_IGNORE and action_int != CheckFSM.ST_ERROR_STATE:
                retlst.append((idstr, statedct[action_int]))
        return retlst


class CheckStockView(SwitcheeView):
    """This is the view that the user will use to check the stock at a particular
    location.
      * The user selects a location
      * The user scans
      * The scanned items are display (expected, unexpected, missing)
      * Once, happy, the user confirms the stock state.
    """

    GO_CHECK_STOCK = 'go_check_stock'

    def __init__(self, contr: widgets.base_controller,
                 parent: widgets.base_widget,
                 idstr: str,
                 attrdct: dict,
                 jsel) -> None:
        title_text = "Check Stock at Specific Locations"
        help_text = """Use the scanner to verify the presence of stock at a specific location."""
        SwitcheeView.__init__(self, contr, parent, idstr, attrdct, jsel,
                              title_text, help_text)
        print("CheckStockView!!!")
        self.location_sel: typing.Optional[html.select] = None
        self.gobutton: typing.Optional[html.textbutton] = None
        self.scanlist: typing.Optional[CheckScanList] = None
        self.rfid_sel_but: typing.Optional[cleverlabels.SliderSwitch] = None
        contr.addObserver(self, base.MSGD_RFID_CLICK)

    def rcvMsg(self,
               whofrom: 'base.base_obj',
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]) -> None:
        if msgdesc == base.MSGD_RFID_CLICK:
            print("GOT SCAN DATA {}".format(msgdat))
            if self.scanlist is not None and msgdat is not None:
                self.scanlist.add_scan(msgdat)
        elif msgdesc == base.MSGD_BUTTON_CLICK:
            if self.location_sel is not None and whofrom == self.location_sel:
                # a new location has been selected: redraw the screen with
                # the new location
                self.Redraw()
            elif self.gobutton is not None and whofrom == self.gobutton:
                # the 'confirm stock' button has been pressed: upload the
                # current stock status for this location to the stocky server.
                menu_num, locidstr = self.location_sel.get_selected()
                if locidstr is not None and self.scanlist is not None:
                    move_lst = self.scanlist.get_move_list()
                    print("locid {}, movelst {}".format(locidstr, move_lst))
                    dd = {'locid': int(locidstr), 'locdat': move_lst}
                    self._contr.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_LOCATION_INFO, dd))
                    print("moving {} items".format(len(move_lst)))
            else:
                super().rcvMsg(whofrom, msgdesc, msgdat)
        else:
            super().rcvMsg(whofrom, msgdesc, msgdat)

    def Redraw(self):
        print("CHECKSTOCK REDRAW")
        self.wcstatus.set_busy(True)
        if self.location_sel is None:
            htext = 'Select the stock location you want to check.'
            self.location_sel = self.wcstatus.get_location_selector(self,
                                                                    "checklocsel",
                                                                    htext, False)
            self.location_sel.addObserver(self, base.MSGD_BUTTON_CLICK)
        else:
            print("Redraw: locsel exists")
            self.wcstatus.update_location_selector(self.location_sel, False)
        # add a RFID label selection button...
        if self.rfid_sel_but is None:
            attrA = {'class': "w3-tag w3-green w3-border-yellow w3-topbar w3-bottombar"}
            attrB = {'class': "w3-tag w3-red w3-border-yellow w3-topbar w3-bottombar"}
            self.rfid_sel_but = cleverlabels.SliderSwitch(self, "scoslider",
                                                          attrA, "Display All items",
                                                          attrB, "RFID tagged items only")
        # here add a table of items at this location...
        ndx, val = self.location_sel.get_selected()
        print("LOCKY: {} {}".format(ndx, val))
        locid = None if val == LOC_NOSEL_ID else val
        loc_items = self.wcstatus.get_location_items(locid)
        # NOTE: ll can also be None...
        # we will receive a list of dicts like this:
        # {'id': 17107, 'last_seen': {}, 'lot_num': 'MKBS0446V',
        #   'notes': 'for use of fridge/freezer probes',
        #   'qcs_location_id': 10046, 'qcs_reag_id': 8158, 'rfid': '(no RFID)'}
        # the id is a reagent item id...
        if self.scanlist is None:
            self.scanlist = CheckScanList(self,
                                          "scocheckscanlist",
                                          self.wcstatus,
                                          loc_items,
                                          self.rfid_sel_but)
        else:
            self.scanlist.reset(loc_items)
        # now add a 'GO' button
        if self.gobutton is None:
            idstr = "checkstock-but"
            attrdct = {'class': button_classes,
                       'title': "Save the current stock status for this location for later upload to QAI",
                       STARATTR_ONCLICK: dict(cmd=CheckStockView.GO_CHECK_STOCK)}
            buttontext = "Confirm Stock Status"
            self.gobutton = html.textbutton(self, idstr, attrdct, buttontext)
            self.gobutton.addObserver(self, base.MSGD_BUTTON_CLICK)
        self.wcstatus.set_busy(False)
        # print("CHECKSTOCK REDRAW DONE")


class LocMutTable(simpletable.simpletable):
    """This class is used when adding new stock to the inventory.
    It displays a list of RFID tags (left column) that have been scanned,
    and allows the user to choose whether they should be added
    or not (right column).
    """
    _LOC_COL = 0
    _ITID_COL = 1
    _RFID_COL = 2
    _DESC_COL = 3
    _OPSTR_COL = 4
    _IGNORE_COL = 5
    _NUM_COLS = 6

    def __init__(self,
                 parent: widgets.base_widget,
                 idstr: str,
                 wcstatus: wcstatus.WCstatus) -> None:
        attrdct: typing.Dict[str, str] = {'class': 'scanlist'}
        simpletable.simpletable.__init__(self, parent, idstr, attrdct, 0, LocMutTable._NUM_COLS)
        self.wcstatus = wcstatus
        self.wcstatus.addObserver(self, base.MSGD_ON_CHANGE)
        self.reset()

    def reset(self) -> None:
        with html.ParentUncouple(self):
            if not self.has_header_row():
                print("adding header...")
                self.add_header_row()
                kattrdct = {'class': "w3-tag w3-blue"}
                for colnum, txt in [(LocMutTable._LOC_COL, "Location"),
                                    (LocMutTable._ITID_COL, "Item ID"),
                                    (LocMutTable._RFID_COL, "RFID label"),
                                    (LocMutTable._DESC_COL, "Description"),
                                    (LocMutTable._OPSTR_COL, "opstring"),
                                    (LocMutTable._IGNORE_COL, "Ignore?")]:
                    kcell = self.getheader(colnum)
                    if kcell is not None:
                        html.label(kcell, "", kattrdct, txt, None)
            # now fill in data rows...
            locdct = self.wcstatus.get_stockloc_dct()
            locmut_dct = self.wcstatus.get_locmut_dct()
            reag_item_dct = self.wcstatus.get_reagent_item_dct()
            # print("RESETTY {}".format(locmut_dct))
            # print("LOCDCT {}".format(locdct))
            # print("REAGDCT {}".format(reag_item_dct))
            ll = []
            for locid, mutlst in locmut_dct.items():
                locname = locdct[locid]
                for ritm_id, opstr, ignore_flag in mutlst:
                    ritm_dct = reag_item_dct[ritm_id]
                    # print("RITM {}".format(ritm_dct))
                    # see whether we have a valid rfid token...
                    has_rfid_label = ritm_dct['rfid'].startswith('CHEM')
                    if has_rfid_label:
                        rfid_str = ritm_dct['rfid']
                    else:
                        rfid_str = "none"
                    lot_num = ritm_dct['lot_num']
                    qcs_reag_id = ritm_dct['qcs_reag_id']
                    dct = dict(locid=locid, locname=locname,
                               item_id=ritm_id, opstr=opstr, rfid_str=rfid_str,
                               ign_flag=ignore_flag,
                               lot_num=lot_num, qcs_reag_id=qcs_reag_id)
                    ll.append(dct)
            # NOTE: might want to sort the list here...
            self.adjust_row_number(len(ll))
            print("dunnn 01: len = {}".format(len(ll)))
            print("LL {}".format(ll))
            for rownum, rdct in enumerate(ll):
                self._add_locmut_row(rownum, rdct)

    def _add_locmut_row(self, rownum: int, ldct: dict) -> None:
        """Add a dict containing information about a single locmut to the table row.

        Args:
           rownum: the table row number to add the information to
           ldct: the dict containing the row information

        Note:
        ldct is of the form:
        {'locid': '10032', 'locname': '647 Powell St', 'item_id': 17713,
          'opstr': 'found', 'rfid_str': 'none', 'ign_flag': False }
        """
        # we retrieve the row to see whether we can reuse some of its columns...
        myrow = self.getrow(rownum)
        if myrow is None:
            print("row number {} is None".format(rownum))
            return
        is_new_row = myrow.isnew
        print("locmut row {} {}".format(rownum, is_new_row))
        # red_label = {'class': "w3-tag w3-red"}
        # grn_label = {'class': "w3-tag w3-green"}
        # org_label = {'class': "w3-tag w3-orange"}
        normal_label = {'class': "w3-tag"}

        loc_name = ldct['locname']
        id_str = ldct['item_id']
        rfid_str = ldct['rfid_str']
        desc_str = "DESC_STR"
        op_str = ldct['opstr']
        ign_str = 'IGN_FLAG'
        helptext = "plain vanilla help text"
        reagent_id = ldct['qcs_reag_id']
        lotnum = ldct['lot_num']
        reag_dct = self.wcstatus.get_reagent_info(reagent_id)
        # put additional information about the reagent into a helptext that will be visible
        # by hovering the mouse over the description element.
        if reag_dct is None:
            desc_str = "reagent id {} , lot: {}".format(reagent_id, lotnum)
            helptext = ""
        else:
            desc_str = "{}".format(reag_dct['name'])
            hazstr = reag_dct['hazards'] or "none"
            helptext = "basetype: {}, cat: {}, hazards: {}, storage: {}, reagent_id: {}".format(reag_dct['basetype'],
                                                                                                reag_dct['category'],
                                                                                                hazstr,
                                                                                                reag_dct['storage'],
                                                                                                reag_dct['id'])
        desc_attrdct = {'class': "w3-tag", 'title': helptext}
        for colnum, coltext, field_attrdct in [(LocMutTable._LOC_COL, loc_name, normal_label),
                                               (LocMutTable._ITID_COL, id_str, normal_label),
                                               (LocMutTable._RFID_COL, rfid_str, normal_label),
                                               (LocMutTable._DESC_COL, desc_str, desc_attrdct),
                                               (LocMutTable._OPSTR_COL, op_str, normal_label),
                                               (LocMutTable._IGNORE_COL, ign_str, normal_label)]:
            if is_new_row:
                kcell = myrow.getcell(colnum)
                if kcell is not None:
                    lab = html.label(kcell, "", field_attrdct, coltext, None)
                    myrow.setcellcontent(colnum, lab)
                else:
                    print("error 99")
                    return
            else:
                lab = myrow.getcellcontent(colnum)
                # print("setty {}".format(lab))
                lab.set_text(coltext)
                if colnum == LocMutTable._DESC_COL:
                    lab.removeAttribute('title')
                    lab.setAttribute('title', helptext)
        myrow.isnew = False

    def get_locmove_list(self) -> dict:
        """Return the selected locmutations from the table.
        Note: for now, just return all of them.
        """
        return self.wcstatus.get_locmut_dct()

    def rcvMsg(self,
               whofrom: 'base.base_obj',
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]) -> None:
        if msgdesc == base.MSGD_ON_CHANGE and whofrom == self.wcstatus:
            # we have received new locmut changes from the server.
            print("GOOTCHA LOCMUT {}".format(msgdat))
            self.reset()
        else:
            super().rcvMsg(whofrom, msgdesc, msgdat)


class UploadLocMutView(SwitcheeView):
    """This is the view that the user will use to review the location changes and upload
    them to QAI.
      * retrieve all location mutations from the stocky server.
      * allow user to ignore certain mutations in the table.
      * Instruct the server to upload the changes to QAI.
    """

    GO_UPLOAD_LOCMUT = 'go_upload_locmut'

    def __init__(self,
                 contr: widgets.base_controller,
                 parent: widgets.base_widget,
                 idstr: str,
                 attrdct: dict,
                 jsel) -> None:
        title_text = "QAI Database Upload Page"
        htext = """Update the QAI system with the modified reagent item statuses
        determined during Stock Check. For this to work, the stocky computer must be
        plugged in to ethernet and you must first log in."""
        SwitcheeView.__init__(self, contr, parent, idstr, attrdct, jsel,
                              title_text, htext)
        self.locmut_tab: typing.Optional[LocMutTable] = None
        self.gobutton: typing.Optional[html.textbutton] = None

    def rcvMsg(self,
               whofrom: 'base.base_obj',
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]) -> None:
        if msgdesc == base.MSGD_BUTTON_CLICK:
            # print("YOYO BLABLA {}".format(whofrom))
            if self.gobutton is not None and whofrom == self.gobutton:
                # the 'upload locmutation' button has been pressed: upload the
                # current stock status for this location to the stocky server.
                print("UPLOAD LOCMUTS!!")
                if self.locmut_tab is not None:
                    print("DO SOMETHING HERE")
                    self._start_report_move()
            else:
                super().rcvMsg(whofrom, msgdesc, msgdat)
        else:
            super().rcvMsg(whofrom, msgdesc, msgdat)

    def Redraw(self):
        """This method is called whenever the view becomes active (because the user
        has selected the respective view button.
        Subclasses should set up their pages in here.

        Note:
        This method could also be called in response to user input.
        Example: the user has chosen a different location, so we must redraw the page...
        """
        print("UPLOAD LOCMUT REDRAW")
        is_logged_in = self.wcstatus.is_QAI_logged_in()
        print("LOGGED IN {}".format(is_logged_in))
        if not is_logged_in:
            html.scoalert("Upload only possible once logged in")
            return
        self._start_locmut_download()
        if self.locmut_tab is None:
            self.locmut_tab = LocMutTable(self, "locmuttab", self.wcstatus)
        # now add a 'GO' button
        if self.gobutton is None:
            idstr = "checkstock-but"
            attrdct = {'class': button_classes,
                       'title': "Upload the current Location changes to QAI.",
                       STARATTR_ONCLICK: dict(cmd=UploadLocMutView.GO_UPLOAD_LOCMUT)}
            buttontext = "Upload to QAI"
            self.gobutton = html.textbutton(self, idstr, attrdct, buttontext)
            self.gobutton.addObserver(self, base.MSGD_BUTTON_CLICK)

    # these are for upload TO the server
    def _start_report_move(self) -> None:
        self.wcstatus.set_busy(True)
        move_lst = self.locmut_tab.get_locmove_list()
        print("movelst {}".format(move_lst))
        dd = {'locmove': move_lst}
        self._contr.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_DO_LOCMUT_REQ, dd))
        print("moving {} items".format(len(move_lst)))
    # def stop_report_move(self) -> None:
    #    self.wcstatus.set_busy(False)

    # these are for download FROM the server
    def _start_locmut_download(self) -> None:
        self.wcstatus.set_busy(True)
        self.wcstatus.refresh_locmut_dct()

    def stop_locmut_download(self) -> None:
        """This is called when the server tells us that a locmut data upload to the webclient
        has completed. The new data is found in self.wcstatus.
        """
        self.wcstatus.set_busy(False)


class ConfigStatusView(SwitcheeView):
    """This is the view that the user will use to review the location changes and upload
    them to QAI.
      * retrieve all location mutations from the stocky server.
      * allow user to ignore certain mutations in the table.
      * instruct the server to upload the changes to QAI.
    """
    def __init__(self,
                 contr: widgets.base_controller,
                 parent: widgets.base_widget,
                 idstr: str,
                 attrdct: dict,
                 jsel) -> None:
        title_text = "Config Status Page"
        htext = """Display some information about the  Stocky server and RFID reader."""
        SwitcheeView.__init__(self, contr, parent, idstr, attrdct, jsel,
                              title_text, htext)
        self.cfg_tab: typing.Optional[simpletable.dict_table] = None

    def Redraw(self):
        # print("CONFIG VIEW REDRAW")
        srv_dct = self.wcstatus.get_server_cfg_data()
        print("CFG: {}".format(srv_dct))
        if srv_dct is not None:
            lst = list(srv_dct.items())
            lst.sort(key=lambda a: a[0])
            if self.cfg_tab is None:
                tab_attrdct = {'class': 'w3-container'}
                self.cfg_tab = simpletable.dict_table(self, "cfg_tab",
                                                      tab_attrdct,
                                                      lst)
            else:
                self.cfg_tab.refill_table(lst)
