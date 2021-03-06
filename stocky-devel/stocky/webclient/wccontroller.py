"""The main program of any stocky webclient consists of a controller class
"""


import typing
import qailib.common.base as base

import qailib.transcryptlib.genutils as genutils
import qailib.common.serversocketbase as serversocketbase
import qailib.transcryptlib.htmlelements as html
import qailib.transcryptlib.forms as forms
import qailib.transcryptlib.widgets as widgets

from webclient.commonmsg import CommonMSG
import webclient.wcviews as wcviews
import webclient.wcstatus as wcstatus

log = genutils.log

LST_NUM = 10

ADDSTOCK_VIEW_NAME = 'addstock'
QAI_DOWNLOAD_VIEW_NAME = 'download'
CHECK_STOCK_VIEW_NAME = 'checkstock'
RADAR_VIEW_NAME = 'radar'
LOCMUT_UPLOAD_VIEW_NAME = 'upload'


STARATTR_ONCLICK = html.base_element.STARATTR_ONCLICK

# NOTE: if these entries have no 'viewclass' entry, a BasicView is used (see init_view)
menulst = [
    {'name': QAI_DOWNLOAD_VIEW_NAME,
     'viewclass': wcviews.DownloadQAIView,
     'button': {'label': 'Download QAI Stock list',
                'title': "Get the current stock list from QAI",
                'id': 'BV2'}
     },
    {'name': ADDSTOCK_VIEW_NAME,
     'viewclass': wcviews.AddNewStockView,
     'button': {'label': 'Add and Dispose of RFID Labels',
                'title': "Add RFID labels to new or existing stock or to dispose of stock",
                'id': 'BV1'}
     },
    {'name': CHECK_STOCK_VIEW_NAME,
     'viewclass': wcviews.CheckStockView,
     'button': {'label': 'Perform Stock Check',
                'title': "Compare scanned items to current stocklist",
                'id': 'BV3'}
     },
    {'name': LOCMUT_UPLOAD_VIEW_NAME,
     'viewclass': wcviews.UploadLocMutView,
     'button': {'label': 'Upload status changes to QAI',
                'title': "Write the reviewed reagent item locations back to QAI",
                'id': 'BV5'}
     },
    {'name': RADAR_VIEW_NAME,
     'viewclass': wcviews.RadarView,
     'button': {'label': 'Locate a Specific Item',
                'title': "Search for an item with a given EPC",
                'id': 'BV4'}
     },
    {'name': 'status',
     'viewclass': wcviews.ConfigStatusView,
     'button': {'label': 'Display Configuration',
                'title': "Display the Stocky server configuration",
                'id': 'BV6'}
     }
    ]


class WebClientController(widgets.base_controller):
    """The class that controls the Stocky webclient program.
    This class is passed a websocket and handles all interactions with the user
    and the stocky server.
    After initialisation, events are handled in rcvMsg(), which should be
    overridden in subclasses.
    """
    def __init__(self, myname: str, ws: serversocketbase.base_server_socket) -> None:
        """

        Args:
           myname: the name of the main program
           ws: the websocket instance used to communicate to the server.
        """
        super().__init__(myname)
        self.numlst: typing.List[int] = []
        ws.addObserver(self, base.MSGD_SERVER_MSG)
        self.wcstatus: typing.Optional[wcstatus.WCstatus] = None
        self.init_view(ws)

    def send_WS_msg(self, msg: CommonMSG) -> None:
        if self.wcstatus is not None:
            self.wcstatus.send_WS_msg(msg)

    def init_view(self, ws: serversocketbase.base_server_socket) -> None:
        """Initialise the servers html elements as required for the application.

        This method must initialise self.wcstatus, passing it the server websocket.
        """
        pass


class stocky_mainprog(WebClientController):
    """The main program for the stocky webclient"""

    def init_view(self, ws: serversocketbase.base_server_socket):
        topdoc = html.getPyElementById('stockyframe')
        if topdoc is not None:
            log('topdoc GOOOTIT')
        else:
            log('topdoc MISSING')
        self.topdoc = topdoc
        # main menu
        menudiv = html.getPyElementById("main-menu-div")
        if menudiv is None:
            log('MENU DIV MISSSING')
        else:
            log("MENU DIV OK")
        self.menudiv = menudiv
        switchattrdct = {"class": "switchview-cls"}
        self.switch = switch = widgets.SwitchView(self, topdoc, "switchview", switchattrdct, None)
        log("SWITCHVIEW OK")
        # initialise the authentication machinery
        popup = forms.modaldiv(topdoc, "loginpopup", "Log In to QAI", {}, "w3-green")
        log("POPUP OK")
        # self.popbutton = popup.get_show_button(theview, "Press Me Now!")
        lf = self.loginform = forms.loginform(popup.get_content_element(),
                                              "scoLLLogin",
                                              popup,
                                              None)
        lf.addObserver(self, base.MSGD_FORM_SUBMIT)
        log("LOGINFORM OK")
        # status bar (top right)
        print("TRYING WCSTATUS")
        self.wcstatus = wcstatus.WCstatus("WCSTAT", ws, self, popup)
        print("WCSTATUS OK")

        # now make switchviews and menubuttons from the menulst
        for mvdct in menulst:
            # add the view
            viewname = mvdct['name']
            viewclassname = mvdct.get('viewclass', widgets.BasicView)
            view = viewclassname(self, switch, viewname, None, None)
            switch.addView(view, viewname)
            # add some identifying text iff required
            vtext = mvdct.get('viewidtext', None)
            if vtext is not None:
                html.h1text(view, vtext)
            # add the menu button for this view...
            butdct = mvdct['button']
            butattdct = {'title': butdct['title'],
                         STARATTR_ONCLICK: {'cmd': 'viewswitch',
                                            'target': viewname},
                         "class": "w3-bar-item w3-button"
                         }
            idstr = butdct['id']
            button_text = butdct['label']
            menu_button = widgets.text_button(self, menudiv, idstr, butattdct, None, button_text)
            # menu_button click events should go to the switchview
            menu_button.addObserver(switch, base.MSGD_BUTTON_CLICK)
            # and also to the respective view...
            menu_button.addObserver(view, base.MSGD_BUTTON_CLICK)

        # initialise the individual Views here...
        switch.switchTo(0)
        self._curlocndx = None

    def setradardata(self, radarinfo: typing.List[typing.Tuple[str, int, float]]):
        """This is a list of string tuples.  (epc code, RI) """
        radar_view = self.switch.getView(RADAR_VIEW_NAME)
        radar_view.set_radardata(radarinfo)

    def set_login_status(self, resdct: dict) -> None:
        """Display the login status in the window"""
        # if not is_logged_in:
        self.loginform.set_login_response(resdct)
        if self.wcstatus is not None:
            self.wcstatus.set_login_response(resdct)

    def start_QAI_download(self):
        """Tell server to start download of QAI data..."""
        self.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_STOCK_INFO_REQ, dict(do_update=True)))

    def addnewstock(self, url: str):
        """Redirect to a new window with the given URL to allow the user to
        add stock."""
        vv = self.switch.getView(ADDSTOCK_VIEW_NAME)
        vv.redirect(url)

    def set_qai_update(self, resdct: dict) -> None:
        """The server has told us about a new QAI update.
        ==> send the new data to wcstatus
        ==? also tell the download view.
        """
        if self.wcstatus is not None:
            self.wcstatus.set_QAIupdate_state(resdct)
        dnl_view = self.switch.getView(QAI_DOWNLOAD_VIEW_NAME)
        dnl_view.stop_download(resdct)

    def set_locmut_update(self, rdct: dict, newhash: str) -> None:
        """The server has told us about a new locmut dict,
        or the server has told us there have been no changes since we last
        polled (rdct will be None in this case).
        ==> send the data to wcstatus if required.
        ==> also tell the locmut view to change its busy status.
        """
        if rdct is not None and self.wcstatus is not None:
            self.wcstatus.set_locmut_dct(rdct, newhash)
        locmut_view = self.switch.getView(LOCMUT_UPLOAD_VIEW_NAME)
        locmut_view.stop_locmut_download()

    def rcvMsg(self, whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]) -> None:
        lverb = True
        if lverb:
            # print("{}.rcvMsg: {}: {} from {}".format(self._idstr, msgdesc, msgdat, whofrom._idstr))
            print("{}.rcvMsg: {} from {}".format(self._idstr, msgdesc, whofrom._idstr))
        if msgdesc == base.MSGD_SERVER_MSG:
            # message from the server.
            if msgdat is None:
                print("msgdat is None")
                return
            cmd = msgdat.get("msg", None)
            val = msgdat.get("data", None)
            if cmd == CommonMSG.MSG_SV_RFID_STATREP and self.wcstatus is not None:
                print("GOT RFID state {}".format(val))
                self.wcstatus.set_RFID_state(val)
                print("state set OK")
            elif cmd == CommonMSG.MSG_SV_RFID_ACTIVITY and self.wcstatus is not None:
                self.wcstatus.set_RFID_state(CommonMSG.RFID_ON)
                self.wcstatus.set_rfid_activity(val)
            elif cmd == CommonMSG.MSG_SV_RAND_NUM:
                # print("GOT number {}".format(val))
                newnum = val
                numlst = self.numlst
                while len(numlst) >= LST_NUM:
                    numlst.pop(0)
                numlst.append(newnum)
                # print("LEN {}".format(len(self.numlst)))
                # self.showlist()
            elif cmd == CommonMSG.MSG_RF_RADAR_DATA:
                self.setradardata(val)
            elif cmd == CommonMSG.MSG_RF_CMD_RESP:
                self.sndMsg(base.MSGD_RFID_CLICK, val)
            elif cmd == CommonMSG.MSG_SV_LOGIN_RES:
                self.set_login_status(val)
            elif cmd == CommonMSG.MSG_SV_LOGOUT_RES and self.wcstatus is not None:
                self.wcstatus.set_logout_status()
            elif cmd == CommonMSG.MSG_SV_STOCK_INFO_RESP:
                self.set_qai_update(val)
            elif cmd == CommonMSG.MSG_SV_ADD_STOCK_RESP:
                self.addnewstock(val)
            elif cmd == CommonMSG.MSG_SV_LOCMUT_RESP:
                rdct, newhash = val['data'], val['hash']
                self.set_locmut_update(rdct, newhash)
            elif cmd == CommonMSG.MSG_SV_SRV_CONFIG_DATA and self.wcstatus is not None:
                self.wcstatus.set_server_cfg_data(val)
            else:
                print("unrecognised server command {}".format(msgdat))
        elif msgdesc == base.MSGD_BUTTON_CLICK:
            print("webclient GOT BUTTON CLICK msgdat={}".format(msgdat))
            if msgdat is None:
                print("msgdat is None")
                return
            cmd = msgdat.get("cmd", None)
            print("webclient GOT BUTTON CLICK CMD {}".format(cmd))
            if cmd == "viewswitch":
                # the switch view does the actual switching on the web client,
                # but we have to tell the server what 'mode' we are in so that
                # it can control the RFID reader appropriately.
                target_view = msgdat.get('target', None)
                radar_on = target_view == RADAR_VIEW_NAME
                self.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_RADAR_MODE, radar_on))
                if target_view is None:
                    print("target_view is None")
                    return
                if target_view == CHECK_STOCK_VIEW_NAME:
                    self.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_RADAR_MODE, False))
                else:
                    print('unknown view target {}'.format(target_view))
            elif cmd == 'roomswitch':
                print("roomswitch not being handled")
                # there is no self.lb...
                # se_ndx, se_val = self.lb.get_selected()
                # print("showchecklist: got LOCKY VBAL '{}'  '{}'".format(se_ndx, se_val))
                # self.showchecklist(se_ndx)
            elif cmd == wcviews.AddNewStockView.GO_ADD_NEW_STOCK or\
                    cmd == wcviews.AddNewStockView.GO_ADD_NEW_RFIDTAG:
                # the GO button of add new stock was pressed:
                # get the selected RFID tags and request an add URL from the server.
                print("GOT addnewstock GO button!")
                vv = self.switch.getView(ADDSTOCK_VIEW_NAME)
                add_info_dct = vv.get_selection_dct()
                add_info_dct['newstock'] = cmd == wcviews.AddNewStockView.GO_ADD_NEW_STOCK
                if add_info_dct is not None:
                    self.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_ADD_STOCK_REQ, add_info_dct))
            else:
                print('webclient: unrecognised cmd {}'.format(cmd))
                return
        elif msgdesc == base.MSGD_FORM_SUBMIT:
            # the login form has sent us a login request. pass this to the server
            # for verification
            print("webclient GOT FORM SUBMIT".format(msgdat))
            un = msgdat.get('username', None) if msgdat is not None else None
            pw = msgdat.get('password', None) if msgdat is not None else None
            dd = {'username': un, 'password': pw}
            self.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_LOGIN_TRY, dd))
            print("OK: sent message")
        else:
            print("unhandled message {}".format(msgdesc))


class rfidping_controller(WebClientController):
    """The main program for the rfid ping test.
    All we do is print out the events to console...
    """

    def rcvMsg(self, whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]) -> None:
        lverb = True
        if lverb:
            # print("{}.rcvMsg: {}: {} from {}".format(self._idstr, msgdesc, msgdat, whofrom._idstr))
            print("{}.rcvMsg: {} from {}".format(self._idstr, msgdesc, whofrom._idstr))
        if msgdesc == base.MSGD_SERVER_MSG:
            # we receive some data from the server...
            # message from the server.
            if msgdat is None:
                print("msgdat is None")
                return
            cmd = msgdat.get("msg", None)
            val = msgdat.get("data", None)
            print("msg:  '{}'".format(cmd))
            print("data: '{}'".format(val))
        elif msgdesc == base.MSGD_COMMS_ARE_UP:
            # this happens when the websocket first comes online. Use it for
            # some initial caching.
            print("COMMS ARE UP")
            # self.wcstatus.set_WS_state(True)
            # self.wcstatus.refresh_locmut_dct()
        elif msgdesc == base.MSGD_COMMS_ARE_DOWN:
            # this happens when the stocky server crashes, taking
            # the websocket connection with it
            print("COMMS ARE DOWN")
            # self.wcstatus.set_WS_state(False)
