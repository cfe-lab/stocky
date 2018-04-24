# This is the 'main program' of the client side program that runs in the browser.
# It is a websocket program

import typing
import qailib.common.base as base

import qailib.transcryptlib.genutils as genutils
import qailib.common.serversocketbase as serversocketbase
import qailib.transcryptlib.serversocket as serversock
import qailib.transcryptlib.htmlelements as html
import qailib.transcryptlib.widgets as widgets
import qailib.transcryptlib.handlebars as handlebars


from commonmsg import CommonMSG
import wcviews

log = genutils.log

LST_NUM = 10

LIST_VIEW_NAME = 'addstock'
CHECK_STOCK_VIEW_NAME = 'checkstock'
RADAR_VIEW_NAME = 'radar'

menulst = [
    {'name': LIST_VIEW_NAME,
     'button': {'label': 'Add New Stock',
                'title': "Add new new stock to the QAI",
                'id': 'BV1'}
     },
    {'name': 'download',
     'button': {'label': 'Download QAI Stock list',
                'title': "Get the current stock list from QAI",
                'id': 'BV2'}
     },
    {'name': CHECK_STOCK_VIEW_NAME,
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
     'button': {'label': 'Upload QAI Stock list',
                'title': "Write the current stock list back to QAI",
                'id': 'BV5'}
     }
    ]


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
        # main mebu
        menudiv = html.getPyElementById("main-menu-div")
        if menudiv is None:
            log('MENU DIV MISSSING')
        else:
            log("MENU DIV OK")
        self.menudiv = menudiv
        switchattrdct = {"class": "switchview-cls"}
        self.switch = switch = widgets.SwitchView(self, topdoc, "switchview", switchattrdct, None)

        statediv = html.getPyElementById("state-div")
        if statediv is None:
            log('STATE DIV MISSSING')
        else:
            log("STATE DIV OK")
        self.statediv = statediv
        ledattrdct = {"title": "Scanner Status"}
        self.status_led = html.LEDElement(statediv,
                                          'statusled',
                                          ledattrdct,
                                          None,
                                          html.LEDElement.RED)
        # now make switchviews and menubuttons from the menulst
        for mvdct in menulst:
            # add the view
            viewname = mvdct['name']
            viewclassname = mvdct.get('viewclass', widgets.BasicView)
            view = viewclassname(self, switch, viewname, None, None)
            switch.addView(view, viewname)
            # add some identifying text...
            h1 = html.h1(view, '{}-h1'.format(viewname), None, None)
            html.textnode(h1, "This is View '{}'".format(viewname))

            # add the menu button
            butdct = mvdct['button']
            butattdct = {'title': butdct['title'],
                         '*buttonpressmsg': {'cmd': 'viewswitch',
                                             'target': viewname},
                         "class": "w3-bar-item w3-button"
                         }
            idstr = butdct['id']
            button_text = butdct['label']
            menu_button = widgets.text_button(self, menudiv, idstr, butattdct, None, button_text)
            # menu_button click events should go to the switchview
            menu_button.addObserver(switch, base.MSGD_BUTTON_CLICK)
        # initialise the individual Views here...
        switch.switchTo(0)
        self._curlocndx = None

    def setstockdata(self, stockdct: dict) -> None:
        # now, prepare the individual views if required
        self._stockloc_lst = stockdct['loclist']
        self._stockitm_lst = stockdct['itemlist']
        self.preparechecklists()
        self.showchecklist(0)

    def _calctab(self, sel_ndx: int) -> str:
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

    def preparechecklists(self):
        self.tabdct = {}
        for ndx, stri in [(ndx, self._calctab(ndx)) for ndx in range(len(self._stockloc_lst))]:
            self.tabdct[ndx] = stri

    def showchecklist(self, sel_ndx: int):
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
                     '*buttonpressmsg': {'cmd': 'roomswitch'},
                     "class": "w3-select locbutton-cls"
                     }
        self.lb = lb = html.getPyElementByIdClass('locky-button', html.select, selattdct)
        lb.addObserver(self, base.MSGD_BUTTON_CLICK)
        # lb = html.select(None, 'locky-button', None, lbjs)
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

    def setradardata(self, radarinfo: typing.List[typing.Tuple[str, int]]):
        """This is a list of string tuples.  (epc code, RI) """
        radar_view = self.switch.getView(RADAR_VIEW_NAME)
        radar_view.set_radardata(radarinfo)

    def showlist(self):
        strval = handlebars.evalTemplate("scolist-template", {"numlist": self.numlst})
        if strval is None:
            log('TEMPLATE FAILED')
        else:
            # log("TEMPLATE {}".format(strval))
            self.switch.getView(LIST_VIEW_NAME).setInnerHTML(strval)

    def rcvMsg(self, whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: base.MSGdata_Type) -> None:
        lverb = True
        if lverb:
            print("rcvMsg: {}: {}".format(msgdesc, msgdat))
        if msgdesc == base.MSGD_SERVER_MSG:
            # message from the server.
            if msgdat is None:
                print("msgdat is None")
                return
            cmd = msgdat.get("msg", None)
            val = msgdat.get("data", None)
            if cmd == CommonMSG.MSG_SV_USB_STATE_CHANGE:
                print("GOT state {}".format(val))
                if val:
                    # set to green
                    self.status_led.setcolour(html.LEDElement.GREEN)
                else:
                    # set to red
                    self.status_led.setcolour(html.LEDElement.RED)
            elif cmd == CommonMSG.MSG_SV_RAND_NUM:
                # print("GOT number {}".format(val))
                newnum = val
                numlst = self.numlst
                while len(numlst) >= LST_NUM:
                    numlst.pop(0)
                numlst.append(newnum)
                # print("LEN {}".format(len(self.numlst)))
                self.showlist()
            elif cmd == CommonMSG.MSG_SV_NEW_STOCK_LIST:
                # the server has sent us a list of all stock items
                self.setstockdata(val)
            elif cmd == CommonMSG.MSG_RF_RADAR_DATA:
                self.setradardata(val)
            else:
                print("unrecognised command {}".format(msgdat))
        elif msgdesc == base.MSGD_BUTTON_CLICK:
            print("webclient GOT BUTTON CLICK")
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
                if target_view is None:
                    print("target_view is None")
                    return
                if target_view == CHECK_STOCK_VIEW_NAME:
                    self.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_STOCK_CHECK, 1))
                elif target_view == RADAR_VIEW_NAME:
                    self.send_WS_msg(CommonMSG(CommonMSG.MSG_WC_RADAR_MODE, 1))
                else:
                    print('unknown view target {}'.format(target_view))
            elif cmd == 'roomswitch':
                se_ndx, se_val = self.lb.get_selected()
                print("showchecklist: got LOCKY VBAL '{}'  '{}'".format(se_ndx, se_val))
                self.showchecklist(se_ndx)
            else:
                print('webclient: unrecognised cmd')
                return


# this is the main program that runs when the page is loaded
log('hello world')
# all we do is open a websocket and start the main program
mysock = serversock.server_socket('scosock', 'ws://localhost:5000/goo', ['/'])
if not mysock.is_open():
    print("FAILED TO PUT ON MY SOCKS!")
main_app = stocky_mainprog('webclient', mysock)
