

# define specific view for the webcloient here

import typing
from org.transcrypt.stubs.browser import window
import qailib.common.base as base

import qailib.transcryptlib.htmlelements as html
import qailib.transcryptlib.forms as forms
import qailib.transcryptlib.simpletable as simpletable
import qailib.transcryptlib.widgets as widgets
import qailib.transcryptlib.SVGlib as SVGlib


BIG_DISTANCE = 99.0


class SwitcheeView(widgets.BasicView):

    def rcvMsg(self,
               whofrom: 'base_obj',
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
        attrdct = attrdct or {}
        attrdct['height'] = attrdct['width'] = '100%'
        attrdct['class'] = 'switchview-cls'
        super().__init__(contr, parent, idstr, attrdct, jsel)
        # size_tup = ('100%', '100%')
        size_tup = None
        self.svg = SVGlib.svg(self, 'scosvg', attrdct, None, size_tup)
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


class AddNewStockView(SwitcheeView):
    """This is the view that the user will use to add new stock to the QAI system.
    a) We allow the user to scan RFID tags and display them.
    b) Once happy, the user hits a button and is redirected to a QAI window.
    """

    def __init__(self, contr: widgets.base_controller,
                 parent: widgets.base_widget,
                 idstr: str,
                 attrdct: dict,
                 jsel) -> None:
        attrdct = attrdct or {}
        attrdct['height'] = attrdct['width'] = '100%'
        attrdct['class'] = 'switchview-cls'
        super().__init__(contr, parent, idstr, attrdct, jsel)
        print("AddNewStockView!!!")
        # self.qai_url: typing.Optional[str] = None
        # self.win = None

    def BLAset_qai_url(self, q: str) -> None:
        self.qai_url = q
        print("AddNewStockView: {}".format(self.qai_url))
        # self.redirect()

    def BLAredirect(self) -> None:
        # this does indeed replace the current window
        # window.location = self.qai_url
        # this opens a new tab or window
        if self.win is None:
            self.win = window.open(self.qai_url)


class DownloadQAIView(SwitcheeView):
    """This is the view that the user will use to sync with the QAI system.
    a) check login status.
    if logged in:
       issue download order.
    else:
       tell user to log in.
    """

    def __init__(self, contr: widgets.base_controller,
                 parent: widgets.base_widget,
                 idstr: str,
                 attrdct: dict,
                 jsel) -> None:
        attrdct = attrdct or {}
        attrdct['height'] = attrdct['width'] = '100%'
        attrdct['class'] = 'switchview-cls'
        super().__init__(contr, parent, idstr, attrdct, jsel)
        self.wcstatus = contr.wcstatus
        print("DownloadStockView!!!")
        self.h1 = html.h1text(self, "QAI Database Download Page")
        # status label..
        self.stat = html.spantext(self, "blastr", {}, "NOT LOGGED IN")
        # spinner
        spin_attrdct = {'class': "w3-display-middle"}
        spin = self.spinner = forms.spinner(self, "myspin", spin_attrdct, forms.spinner.SPN_SPINNER, 50)
        spin.set_visible(False)
        # prepare a span for the status table
        self.stat_tab = None
        
    def Redraw(self):
        """Start the download if we are loggged in."""
        is_logged_in = self.wcstatus.is_QAI_logged_in()
        print("LOGGED IN {}".format(is_logged_in))
        if is_logged_in:
            self._start_download()
        else:
            self.stat.set_text("NOT LOGGED IN. Please log in and try again...")

    def _start_download(self) -> None:
        self.stat.set_text("Downloading QAI data...")
        spin = self.spinner
        spin.set_visible(True)
        spin.set_spin(True)
        self._contr.start_QAI_download()

    def stop_download(self, resdct: dict) -> None:
        """ This is called when the server tells us that the QAI download has completed."""
        self.stat.set_text("Downloading successful...")
        tmp_dct = resdct.get('db_stats', None)
        print("SB stats {}".format(tmp_dct))
        db_stat_dct = dict(tmp_dct)
        if self.stat_tab is None:
            self.stat_tab = simpletable.dict_table(self, "stat_tab", {}, list(db_stat_dct.items()))
        else:
            self.stat_tab.update_table(db_stat_dct)
        self.spinner.set_spin(False)
