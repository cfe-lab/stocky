# This is the 'main program' of the client side program that runs in the browser.
# It is a websocket program

import qailib.common.base as base

import qailib.transcryptlib.genutils as genutils
import qailib.common.serversocketbase as serversocketbase
import qailib.transcryptlib.serversocket as serversock
import qailib.transcryptlib.htmlelements as html
import qailib.transcryptlib.widgets as widgets
# import qailib.transcryptlib.guiforms as guiforms


import clientUI

log = genutils.log

CRUD_update = serversocketbase.CRUD_update


class webapp_controller(widgets.socket_controller):
    """This is the 'main application' that runs on the client side.
    Essentially, after initialisation, it just reacts to events from
    either
    a) the server by incoming_events()
    b) user events by button_press()
    """

    def data_cache_ready(self, whofrom: base.base_obj, data_in: base.MSGdata_Type):
        """This method is called when the datacache has established a connection
        to the server.
        ==> we can get information about out GUI elements, and start building it.
        """
        ec = self._dcache.exitcode
        errmsg = self._dcache.errmsg
        print("controller: got datacache ready {} {}".format(ec, errmsg))
        self.init_view()

    def builduserdashboard(self, view: widgets.BasicView, uid: str) -> None:
        html.create_elementstring(view, 'dashtitle', None,
                                  html.h1, "User Dashboard")
        # formmodelname = 'QLUser'
        formmodelname = 'updateUserInputType'
        formdefdct = self._dcache.getFormDefDict(formmodelname, 'all')
        print("BUILDY {}, id = {}".format(formdefdct is not None, uid))
        if formdefdct is None:
            log('formdefdct is None: cannot build dashboard')
            return
        modelname = 'User'
        my_rec = self._dcache[modelname]
        print("myrec: {}  {}".format(my_rec is not None, len(my_rec.get_list())))
        my_user_data = my_rec[uid]
        print("USERDAT '{}'".format(my_user_data))
        # formbuilder = guiforms.HtmlFormBuilder(formdefdct)
        # self.userformwidge = widgets.FormWidget(self, view, 'formwidge',
        #                                       None,
        #                                       formbuilder,
        #                                       my_user_data)

    def form_submit(self, whofrom: base.base_obj, data_in: base.MSGdata_Type) -> None:
        """This function is called when a form has verified its input fields
        and has data to provide. This is sent in the data_in argument.
        """
        print("GOT FORM_SUBMIT : {}".format(data_in))
        if whofrom == self.userformwidge:
            print("submitting mods...")
            issued_ok = self._dcache.issue_CRUD(CRUD_update, 'User', data_in)
            print("submission succeeded: {}".format(issued_ok))

    def OLDsetuserlst(self, view: widgets.BasicView, htmllst: list) -> None:
        listel = html.ul(view, 'userlist', {})
        for htmlstr in htmllst:
            list_item = html.li(listel, None, {})
            el = html.table(list_item, None, {})
            el.setInnerHTML(htmlstr)

    def init_view(self) -> None:
        """Build page elements required for the app.
        Strategy: the main elements are predefined in the HTML DOM.
        Find the required bits and add our application-specific elements.

        We put all of the application contents into a SwitchView (displays only
        one subview at a time), with each subview being a 'fish view'.
        """
        self.build_menus()
        topdoc = html.getPyElementById('SCOpage-cont')
        if topdoc is not None:
            log('topdoc GOOOTIT')
        else:
            log('topdoc MISSING')
        self._switch = switch = widgets.SwitchView(self, topdoc, "switchview", None)
        prefix = 'view'
        switch.addView(make_testview(switch, self, 'one'), 'one-view')
        # switch.addView(make_view_fish(switch, self, 'one', prefix), 'one-view')
        switch.addView(make_view_fish(switch, self, 'two', prefix), 'two-view')
        switch.addView(make_view_fish(switch, self, 'red', prefix), 'red-view')
        # bluview is going to be the dashboard...
        # self.bluview = bluview = make_view_fish(switch, self, 'blu', prefix)
        self.bluview = bluview = widgets.BasicView(self, switch, 'blu-view', None)
        # show_stuff(bluview)
        switch.addView(bluview, 'blu-view')
        switch.switchTo('blu-view')
        uid, uname, currole = self._dcache.get_user_info()
        self.builduserdashboard(self.bluview, uid)
        self.men_lst.addObserver(switch, base.MSGD_BUTTON_CLICK)

    def build_menus(self) -> None:
        """ Build the main menu items
        A) the menu items on the left hand page
        B) the top menu bar
        """
        # look for the element main-menu-div and add a UL of elements
        menucon_el = html.getPyElementById('main-menu-div')
        if menucon_el is None:
            log("menucon FAIL")

        self.men_lst = menlst = widgets.MenuList(self, menucon_el, 'main-menu-OBJlst', {})
        prefix = 'menu'
        for fishname in ['one', 'two', 'red', 'blu']:
            menlst.addItem(make_menu_fish(menlst, self, fishname, prefix))

        # B) the top menu bar
        self.topbar_el = topbar_el = html.getPyElementById('top-bar-div')
        if menucon_el is None:
            log("top-bar-div FAIL")
        else:
            log("gotcha top menu")
            self._statusbar = clientUI.StatusBar(self, topbar_el,
                                                 'status-bar',
                                                 self._dcache)

    def button_press(self, whofrom: base.base_obj, msgdat: base.MSGdata_Type) -> None:
        """This function is called when any button is pressed in the browser.
        The argument is the idstring of the sending button element.
        msgdat is any message the button might have sent as well.
        """
        whofrom_id = whofrom._idstr
        print('BUTTONPRESS!!! {} {}'.format(whofrom_id, msgdat))
        # see whether this is a view switch event
        if whofrom_id == 'usermod-button':
            # user wants to modify her user profile:
            # new_user_info = self.userformwidgets.getFormData()
            # print("NOW HAVE '{}".format(new_user_info))
            # self._dcache.issue_CRUD(CRUD_update, 'User', new_user_info)
            pass

    def log_event(self, whofrom: base.base_obj, data_in: base.MSGdata_Type) -> None:
        """ This method is called whenever the datacache issues a logging event.
        NOTE: the data is provided as a python dictionary with
        'exitcode' and 'errmsg' keys.
        """
        print("LOG: '{}'".format(data_in["errmsg"]))


def make_view_fish(parent: widgets.base_widget,
                   contr: widgets.base_controller,
                   whichfish: str,
                   id_prefix: str) -> widgets.BasicView:
    attdct = {'title': "the {} fish help text".format(whichfish)}
    idstr = '{}{}fishid'.format(id_prefix, whichfish)
    urlstr = '/static/assets/img/{}-fish.png'.format(whichfish)
    altstr = '{}-FISH-pic'.format(whichfish)
    vv = widgets.BasicView(contr, parent, idstr, attdct)
    widgets.ImageWidget(contr, vv, idstr, attdct, urlstr, altstr)
    return vv


def make_testview(parent: widgets.base_widget,
                  contr: widgets.base_controller,
                  viewname: str) -> widgets.BasicView:
    idstr = '{}{}fishid'.format('view', viewname)
    attdct: dict = {}
    view = widgets.BasicView(contr, parent, idstr, attdct)
    el = html.table(view, 'usertable', dict(border=1, width='100%'))
    htmlstr = """
 <tr> <th>one </th> <th> two <th> <th> three <th> </tr>
 <tr> <td>oneDD </td> <td> twoDD <td> <td> threeDD <td> </tr>
 """
    el.setInnerHTML(htmlstr)
    # tbody = el._el.tBodies[0]
    # tbody.innerHTML = htmlstr
    return view


def make_menu_fish(parent: widgets.base_widget,
                   contr: widgets.base_controller, whichfish: str, id_prefix: str) -> widgets.base_widget:
    attdct = {'title': "the {} fish help text".format(whichfish),
              '*buttonpressmsg': {'cmd': 'viewswitch',
                                  'target': '{}-view'.format(whichfish)
                                  }
              }
    idstr = '{}{}-fishid'.format(id_prefix, whichfish)
    urlstr = '/static/assets/img/{}-fish.png'.format(whichfish)
    altstr = '{}-FISH-pic'.format(whichfish)
    # vv = widgets.BasicView(contr, parent, idstr, attdct)
    img = widgets.ImageWidget(contr, parent, idstr, attdct, urlstr, altstr)
    return img


def maketable(parent: html.base_element) -> widgets.sort_table:
    cc = ('first', 'last', 'skill')
    dd = [('jon', 'bloggs', 'fencer'),
          ('barb', 'sheppard', 'writer'),
          ('Mandy', 'Okemole', 'dancer'),
          ('barb', 'johnson', 'script editor'),
          ('Stephen', 'Schwartz', 'programmer'),
          ('Wilbur', 'FunnyDuddy', 'singer')]
    lst = [dict(zip(cc, d)) for d in dd]
    tab = widgets.sort_table(parent, 'scotable', {}, cc, lst)
    return tab


def makelist(parent: html.base_element) -> None:
    lst = [("ONE FISH", {'href': 'webclient.html'}),
           ("TWO FISH", {}),
           ("RED FISH", {}),
           ("BLUE FISH", {})]
    widgets.writelist(parent, 'll1', None, lst, True)
    widgets.writelist(parent, 'll2', None, lst, False)


def show_stuff(topdoc: html.base_element) -> dict:
    """Generate a selection of html elements into the topdoc."""
    eldct = {}
    for txt, idstr, hh in [("HH 1", "scoh1", html.h1),
                           ("HH 2", "scoh2", html.h2),
                           ("HH 3", "scoh3", html.h3),
                           ("para #TODO: ext", "scopara", html.p),
                           ("link text", "scolink", html.a),
                           ("divvy", "scodiv", html.div),
                           ("spanny", "scospan", html.span)]:
        hdr_el = hh(topdoc, idstr, {'title': 'this is topdoc help text'})
        html.textnode(hdr_el, txt)
        eldct[idstr] = hdr_el
    makelist(topdoc)
    maketable(topdoc)
    return eldct


# this is the main program that runs when the page is loaded
log('hello world')
# all we do is open a websocket and start the main program
mysock = serversock.server_socket('scosock', 'ws://localhost:8000/', ['bla'])
if not mysock.is_open():
    print("FAILED TO PUT ON MY SOCKS!")
main_app = webapp_controller('webclient', mysock)
