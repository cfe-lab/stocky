import typing
import qailib.common.base as base

import qailib.transcryptlib.genutils as genutils
import qailib.common.serversocketbase as serversocketbase
import qailib.transcryptlib.htmlelements as html
import qailib.transcryptlib.forms as forms
import qailib.transcryptlib.widgets as widgets
import qailib.transcryptlib.handlebars as handlebars
# import qailib.transcryptlib.simpletable as simpletable


from commonmsg import CommonMSG
import wcviews
import wcstatus

log = genutils.log

LST_NUM = 10

ADDSTOCK_VIEW_NAME = 'addstock'
QAI_DOWNLOAD_VIEW_NAME = 'download'
CHECK_STOCK_VIEW_NAME = 'checkstock'
RADAR_VIEW_NAME = 'radar'

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
     'button': {'label': 'Add New Stock',
                'title': "Add new new stock to the QAI",
                'id': 'BV1'}
     },
    {'name': CHECK_STOCK_VIEW_NAME,
     'viewclass': wcviews.CheckStockView,
     'button': {'label': 'Perform Stock Check',
                'title': "Compare scanned items to current stocklist",
                'id': 'BV3'}
     },
    {'name': RADAR_VIEW_NAME,
     'viewclass': wcviews.RadarView,
     'button': {'label': 'Locate a Specific Item',
                'title': "Search for an item with a given EPC",
                'id': 'BV4'}
     },
    {'name': 'upload',
     'viewidtext': "This is view Upload",
     'button': {'label': 'Upload QAI Stock list',
                'title': "Write the current stock list back to QAI",
                'id': 'BV5'}
     }
    ]


def sco_submit():
    log("SCOSUBMIIIT")


class stocky_mainprog(widgets.base_controller):
    def __init__(self, myname: str, ws: serversocketbase.base_server_socket) -> None:
        super().__init__(myname)
        self._ws = ws
        ws.addObserver(self, base.MSGD_SERVER_MSG)
        ws.addObserver(self, base.MSGD_COMMS_ARE_UP)
        self.numlst: typing.List[int] = []
        self.init_view()

    def send_WS_msg(self, msg: CommonMSG) -> None:
        """Send a message to the server via websocket."""
        self._ws.send(msg.as_dict())

    def init_view(self):
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
        popup = forms.modaldiv(topdoc, "loginpopup", "Log In to QAI", {}, "w3-teal")
        log("POPUP OK")
        # self.popbutton = popup.get_show_button(theview, "Press Me Now!")
        lf = self.loginform = forms.loginform(popup.get_content_element(),
                                              "scoLLLogin",
                                              popup,
                                              None)
        lf.addObserver(self, base.MSGD_FORM_SUBMIT)
        log("LOGINFORM OK")

        # status bar (top right)
        log("TRYING WCSTATUS")
        self.wcstatus = wcstatus.WCstatus("WCSTAT", self, popup)
        log("WCSTATUS OK")

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

    def BLA_calctab(self, sel_ndx: int) -> typing.Optional[str]:
        """Generate the html string for location index sel_ndx"""
        # determine the list of locations to display
        display_loc_lst = [{'name': loc,
                            'key': '{}'.format(ndx),
                            'isselected': ndx == sel_ndx} for ndx, loc in enumerate(self._stockloc_lst)]
        # select the items at this location from the stock_list
        scan_lst, ii = [], 0
        stattab = ['FOUND', 'ABSENT', 'UNEXPECTED']
        for locndx, itm_str, tagnum, helptext in self._stockitm_lst:
            if locndx == sel_ndx:
                scan_lst.append({'name': itm_str,
                                 'id': tagnum,
                                 'helptext': helptext,
                                 'status': stattab[ii % 3]})
                ii += 1
        strval = handlebars.evalTemplate("checkstock-template", {"loclist": display_loc_lst,
                                                                 "scanlist": scan_lst})
        return strval

    def BLApreparechecklists(self):
        self.tabdct = {}
        for ndx, stri in [(ndx, self._calctab(ndx)) for ndx in range(len(self._stockloc_lst))]:
            self.tabdct[ndx] = stri

    def BLAshowchecklist(self, sel_ndx: int):
        """Show the list of stock items that are located at sel_ndx.
        """
        maxlen = len(self._stockloc_lst)
        print("setting loc '{}', len: {}".format(sel_ndx, maxlen))
        if sel_ndx < 0 or sel_ndx >= maxlen or self._curlocndx == sel_ndx:
            return
        # strval = self._calctab(sel_ndx)
        newstrval = self.tabdct.get(sel_ndx, None)
        if newstrval is None:
            log('TEMPLATE FAILED')
            return
        # if we have reached this point, we are going to make the switch
        html.setCursorBusy(True)
        check_view = self.switch.getView(CHECK_STOCK_VIEW_NAME)
        # switch out the innerHTML elements. Save the current innerHTML for later use
        # NOTE: this does not work -- the table references become all mixed up...
        # if self._curlocndx is not None:
        #    oldstr = check_view.getInnerHTML()
        #    log("OLD TEMPLATE {} {}".format(self._curlocndx, oldstr))
        #    self.tabdct[self._curlocndx] = oldstr
        self._curlocndx = sel_ndx
        check_view.setInnerHTML(newstrval)
        selattdct = {'title': 'Select the stock location you want to verify',
                     STARATTR_ONCLICK: {'cmd': 'roomswitch'},
                     "class": "w3-select locbutton-cls"
                     }
        self.lb = lb = typing.cast(html.select,
                                   html.getPyElementByIdClass('locky-button',
                                                              html.select, selattdct))
        if lb is not None:
            lb.addObserver(self, base.MSGD_BUTTON_CLICK)
            print('got LOCKY {}'.format(lb))
            se_ndx, se_val = lb.get_selected()
            print('got LOCKY VBAL {}  {}'.format(se_ndx, se_val))
        # we do not sort the table after all...
        # tabby = html.getPyElementByIdClass('scantable', html.table, None)
        # print('got TABBY {}'.format(tabby))
        # rowlst = tabby.getrows()
        # print('got tabby rows len {}'.format(len(rowlst)))
        # print('got tabby rows {}'.format(rowlst))
        # tabby.columnsort(2)
        # tabvals = [row.getcells() for row in rowlst[1:]]
        html.setCursorBusy(False)

    def setradardata(self, radarinfo: typing.List[typing.Tuple[str, int, float]]):
        """This is a list of string tuples.  (epc code, RI) """
        radar_view = self.switch.getView(RADAR_VIEW_NAME)
        radar_view.set_radardata(radarinfo)

    def BLAshowlist(self):
        strval = handlebars.evalTemplate("scolist-template", {"numlist": self.numlst})
        if strval is None:
            log('TEMPLATE FAILED')
        else:
            # log("TEMPLATE {}".format(strval))
            self.switch.getView(ADDSTOCK_VIEW_NAME).setInnerHTML(strval)

    def set_login_status(self, resdct: dict) -> None:
        """Display the login status in the window"""
        # if not is_logged_in:
        self.loginform.set_login_response(resdct)
        self.wcstatus.set_login_response(resdct)

    def start_QAI_download(self):
        """Tell server to start download of QAI data..."""
        self.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_STOCK_INFO_REQ, dict(do_update=True)))

    def addnewstock(self, url: str):
        """redirect to a new window with the given URL ro allow user to
        add stock."""
        vv = self.switch.getView(ADDSTOCK_VIEW_NAME)
        vv.redirect(url)

    def set_qai_update(self, resdct: dict) -> None:
        """ the server has told us about a new QAI update.
        ==> tell the wcstatus icons
        ==? also tell the download view.
        """
        self.wcstatus.set_QAIupdate_state(resdct)
        dnl_view = self.switch.getView(QAI_DOWNLOAD_VIEW_NAME)
        dnl_view.stop_download(resdct)

    def rcvMsg(self, whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]) -> None:
        lverb = True
        if lverb:
            print("{}.rcvMsg: {}: {} from {}".format(self._idstr, msgdesc, msgdat, whofrom._idstr))
        if msgdesc == base.MSGD_SERVER_MSG:
            # message from the server.
            if msgdat is None:
                print("msgdat is None")
                return
            cmd = msgdat.get("msg", None)
            val = msgdat.get("data", None)
            if cmd == CommonMSG.MSG_SV_USB_STATE_CHANGE:
                print("GOT USB state {}".format(val))
                self.wcstatus.set_RFID_state(val)
            elif cmd == CommonMSG.MSG_SV_RFID_STATREP:
                print("GOT RFID state {}".format(val))
                self.wcstatus.set_RFID_state(val)
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
            elif cmd == CommonMSG.MSG_SV_LOGOUT_RES:
                self.wcstatus.set_logout_status()
            elif cmd == CommonMSG.MSG_SV_RFID_ACTIVITY:
                self.wcstatus.set_rfid_activity(val)
            elif cmd == CommonMSG.MSG_SV_STOCK_INFO_RESP:
                self.set_qai_update(val)
            elif cmd == CommonMSG.MSG_SV_ADD_STOCK_RESP:
                self.addnewstock(val)
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
                se_ndx, se_val = self.lb.get_selected()
                print("showchecklist: got LOCKY VBAL '{}'  '{}'".format(se_ndx, se_val))
                self.showchecklist(se_ndx)
            elif cmd == 'logout':
                # the logout button was pressed
                self.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_LOGOUT_TRY, 1))
            elif cmd == wcviews.AddNewStockView.GO_ADD_NEW_STOCK:
                # the GO button of ad new stock was pressed:
                # get the selected RFID tags and request an add URL from the server.
                print("GOT addnewstock GO button!")
                vv = self.switch.getView(ADDSTOCK_VIEW_NAME)
                if vv.scanlist is not None:
                    add_rfid_lst = vv.scanlist.get_active_tags()
                    print("newstock {}".format(add_rfid_lst))
                    if len(add_rfid_lst) > 0:
                        self.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_ADD_STOCK_REQ, add_rfid_lst))
            else:
                print('webclient: unrecognised cmd {}'.format(cmd))
                return
        elif msgdesc == base.MSGD_COMMS_ARE_UP:
            pass
            # print("sending config request to server")
            # self.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_CONFIG_REQUEST, 1))
        elif msgdesc == base.MSGD_FORM_SUBMIT:
            # the login form has sent us a login request. pass this to the server
            # for verification
            print("webclient GOT FORM SUBMIT".format(msgdat))
            un = msgdat.get('username', None) if msgdat is not None else None
            pw = msgdat.get('password', None) if msgdat is not None else None
            dd = {'username': un, 'password': pw}
            self.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_LOGIN_TRY, dd))
        else:
            print("unhandled message {}".format(msgdesc))
