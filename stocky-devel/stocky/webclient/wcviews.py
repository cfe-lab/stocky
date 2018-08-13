
# define specific views for the webclient here
import typing
from org.transcrypt.stubs.browser import window
import qailib.common.base as base

import qailib.transcryptlib.htmlelements as html
import qailib.transcryptlib.forms as forms
import qailib.transcryptlib.simpletable as simpletable
import qailib.transcryptlib.widgets as widgets
import qailib.transcryptlib.SVGlib as SVGlib

# NOTE: would like to import this here for typing, but it leads to javascript
# run time errors because the modules import each other)
# import wccontroller

import wcstatus

BIG_DISTANCE = 99.0

STARATTR_ONCLICK = html.base_element.STARATTR_ONCLICK

LOC_NOSEL_ID = wcstatus.WCstatus.LOC_NOSEL_ID


class SwitcheeView(widgets.BasicView):
    def __init__(self, contr: widgets.base_controller,
                 parent: widgets.base_widget,
                 idstr: str,
                 attrdct: dict,
                 jsel, titletext: str, helptext: str) -> None:
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
                print("msgdat is None")
                return
            cmd = msgdat.get("cmd", None)
            # val = msgdat.get("target", None)
            # print("VIEW GOT {} {}".format(cmd, val))
            if cmd == "viewswitch":
                self.Redraw()

    def Redraw(self):
        """This method called whener the view becomes active (because the user
        has selected the respective view button.
        Subclasses should set up their pages in here.
        """
        print("EMPTY VIEW REDRAW")


class RadarView(SwitcheeView):
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


class ScanList(simpletable.simpletable):
    _RFID_COL = 0
    _ACTIV_COL = 1

    def __init__(self, parent: widgets.base_widget, idstr: str) -> None:
        attrdct: typing.Dict[str, str] = {'class': 'scanlist'}
        super().__init__(parent, idstr, attrdct, 0, 2)
        self.reset()

    def reset(self):
        """Empty the list and display a placeholder..."""
        self._tklst = []
        self._tkdct = {}
        self.delete_rows()
        if not self.has_header_row():
            self.add_header_row()
            kattrdct = {'class': "w3-tag w3-blue"}
            for colnum, txt in [(ScanList._RFID_COL, "RFID label"),
                                (ScanList._ACTIV_COL, "Selected?")]:
                kcell = self.getheader(colnum)
                if kcell is not None:
                    html.label(kcell, "", kattrdct, txt, None)

    def _add_token(self, newtk: str) -> None:
        """Add a new token string to the list."""
        if newtk not in self._tkdct:
            on_attrdct = {'class': "w3-tag w3-green"}
            off_attrdct = {'class': "w3-tag w3-red"}
            on_text = "Add to QAI"
            off_text = "Ignore"
            # add the new token...
            rownum = self.append_row()
            kcell = self.getcell(rownum, ScanList._RFID_COL)
            if kcell is not None:
                kattrdct = {'class': "w3-tag w3-red"}
                html.label(kcell, "", kattrdct, newtk, None)
            vcell = self.getcell(rownum, ScanList._ACTIV_COL)
            if vcell is not None:
                tog_lab = forms.ToggleLabel(vcell, "rfid_lsb{}".format(rownum),
                                            on_attrdct, on_text,
                                            off_attrdct, off_text)
                self._tkdct[newtk] = tog_lab
            self.set_alignment(rownum, ScanList._ACTIV_COL, "center")

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
        for tag, cont in newdat:
            if (tag == 'EP' or tag == 'BC') and cont[:4] == 'CHEM':
                self._add_token(cont)

    def get_active_tags(self) -> typing.List[str]:
        """Return the list of RFID tags (in column 0) if the column 1
        state is OK.
        """
        return [k for k, tog in self._tkdct.items() if tog.is_A_state()]


class AddNewStockView(SwitcheeView):
    """This is the view that the user will use to add new stock to the QAI system.
    a) We allow the user to scan RFID tags and display them.
    b) Once happy, the user hits a button and is redirected to a QAI window.
    """

    GO_ADD_NEW_STOCK = 'go_add_new_stock'

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
        self.location_sel: typing.Optional[html.select] = None
        self.gobutton: typing.Optional[html.textbutton] = None
        self.scanlist: typing.Optional[ScanList] = None
        self._initelements()
        contr.addObserver(self, base.MSGD_RFID_CLICK)

    def _initelements(self):
        if self.location_sel is None:
            htext = 'Select the stock location you want to add new items to'
            self.location_sel = self.wcstatus.get_location_selector(self,
                                                                    "addlocsel",
                                                                    htext, True)
        else:
            self.wcstatus.update_location_selector(self.location_sel, True)
        # list of scanned RFID tags...
        if self.scanlist is None:
            self.scanlist = ScanList(self, "scocanlist")
        else:
            self.scanlist.reset()
        # now add a 'GO' button
        if self.gobutton is None:
            idstr = "addloc-but"
            attrdct = {'class': 'w3-button',
                       'title': "Add selected RFID tags to QAI",
                       STARATTR_ONCLICK: dict(cmd=AddNewStockView.GO_ADD_NEW_STOCK)}
            buttontext = "Add to QAI"
            self.gobutton = html.textbutton(self, idstr, attrdct, buttontext)
            self.gobutton.addObserver(self._contr, base.MSGD_BUTTON_CLICK)

    def Redraw(self):
        """This method called whener the view becomes active (because the user
        has selected the respective view button.
        Subclasses should set up their pages in here.
        """
        print("Add New stock REDRAW")
        self._initelements()

    def rcvMsg(self,
               whofrom: 'base.base_obj',
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]) -> None:
        if msgdesc == base.MSGD_RFID_CLICK:
            print("GOT SCAN DATA {}".format(msgdat))
            if self.scanlist is not None and msgdat is not None:
                self.scanlist.add_scan(msgdat)
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
        if self.location_sel is None:
            return None
        ndx, val = self.location_sel.get_selected()
        print("LOCKY {} {}".format(ndx, val))
        locid = None if val == LOC_NOSEL_ID else val
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
    """This is the view that the user will use to sync with the QAI system.
    a) check login status.
    if logged in:
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

        # status label and spinner are in a cell-row (so they appear side-by side)
        cl_attrdct = {'class': 'w3-cell-row'}
        cellrow = html.div(self, "cldiv", cl_attrdct, None)
        # status label..
        # cc_attrdct = {'class': 'w3-container w3-cell'}
        # self.stat = html.spantext(cellrow, "blastr", cc_attrdct, "NOT LOGGED IN")
        # spinner
        spin_sz_pixels = 50
        # span_attrdct = {'height': '{}px'.format(spin_sz_pixels),
        #                'class': 'w3-container w3-cell'}
        # spinnerspan = html.span(cellrow, "spinnerspan", span_attrdct, None)
        # spin_attrdct = {'class': "w3-display-middle"}
        spin_attrdct = {'title': "Download activity from QAI"}
        self.spinner = forms.spinner(cellrow, "myspin",
                                     spin_attrdct, forms.spinner.SPN_SPINNER,
                                     spin_sz_pixels)
        self.stat_tab: typing.Optional[simpletable.dict_table] = None

    def Redraw(self):
        """Start the download if we are loggged in."""
        is_logged_in = self.wcstatus.is_QAI_logged_in()
        print("LOGGED IN {}".format(is_logged_in))
        if is_logged_in:
            self._start_download()

    def _start_download(self) -> None:
        # self.stat.set_text("Downloading QAI data...")
        spin = self.spinner
        spin.set_spin(True)
        # typing.cast(wccontroller.stocky_mainprog, self._contr).start_QAI_download()
        self._contr.start_QAI_download()

    def stop_download(self, resdct: dict) -> None:
        """ This is called when the server tells us that the QAI download has completed."""
        # self.stat.set_text("Downloading successful...")
        tmp_dct = resdct.get('db_stats', None)
        print("SB stats {}".format(tmp_dct))
        db_stat_dct = dict(tmp_dct)
        if self.stat_tab is None:
            tab_attrdct = {'class': 'w3-container'}
            self.stat_tab = simpletable.dict_table(self, "stat_tab",
                                                   tab_attrdct,
                                                   list(db_stat_dct.items()))
        else:
            self.stat_tab.update_table(db_stat_dct)
        self.spinner.set_spin(False)


class CheckStockView(SwitcheeView):
    """This is the view that the user will use to check the stock at a particular
    location.
    a) The user selects a location
    b) The user scans
    c) The scanned items are display (expected, unexpected, missing)
    d) Once, happy, the user confirms the stock state.
    """

    GO_ADD_NEW_STOCK = 'go_add_new_stock'

    def __init__(self, contr: widgets.base_controller,
                 parent: widgets.base_widget,
                 idstr: str,
                 attrdct: dict,
                 jsel) -> None:
        title_text = "Check Stock at Specific Locations"
        help_text = """Use the scanner to verify the presence of stock at a specific location."""
        SwitcheeView.__init__(self, contr, parent, idstr, attrdct, jsel,
                              title_text, help_text)
        print("AddNewStockView!!!")
        self.location_sel: typing.Optional[html.select] = None
        self.gobutton: typing.Optional[html.textbutton] = None
        self.scanlist: typing.Optional[ScanList] = None
        self._initelements()
        contr.addObserver(self, base.MSGD_RFID_CLICK)

    def rcvMsg(self,
               whofrom: 'base.base_obj',
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]) -> None:
        if msgdesc == base.MSGD_RFID_CLICK:
            print("GOT SCAN DATA {}".format(msgdat))
            if self.scanlist is not None and msgdat is not None:
                self.scanlist.add_scan(msgdat)
        else:
            super().rcvMsg(whofrom, msgdesc, msgdat)

    def _initelements(self):
        if self.location_sel is None:
            htext = 'Select the stock location you want to check.'
            self.location_sel = self.wcstatus.get_location_selector(self,
                                                                    "checklocsel",
                                                                    htext)
        else:
            self.wcstatus.update_location_selector(self.location_sel)
        # here add a table of items at this location...

        # now add a 'GO' button
        if self.gobutton is None:
            idstr = "addloc-but"
            attrdct = {'class': 'w3-button',
                       'title': "Add selected RFID tags to QAI",
                       STARATTR_ONCLICK: dict(cmd=AddNewStockView.GO_ADD_NEW_STOCK)}
            buttontext = "Add to QAI"
            self.gobutton = html.textbutton(self, idstr, attrdct, buttontext)
            self.gobutton.addObserver(self._contr, base.MSGD_BUTTON_CLICK)

    def Redraw(self):
        """Start the download if we are loggged in."""
        print("CHECKSTOCK REDRAW")
        self._initelements()
