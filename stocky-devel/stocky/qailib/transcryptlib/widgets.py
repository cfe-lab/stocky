"""Define controllers and widgets.
   A controller is simply and base_ob with some predefined methods that is used as
   a main program. The controller has predefined ways of reacting to events such as
   button clocks etc.
   A widget is an html element associated with a controller. It sends its events to
   the controllerfor handling.
"""

import typing as T
# 2018-09-07: importing typing in the following way leads to javascript run-time
# errors. Reported as transcrypt Issue #555
# from typing import Dict, List, Tuple, Type, Callable, Optional, Union

import qailib.transcryptlib.genutils as genutils
import qailib.common.base as base
import qailib.transcryptlib.htmlelements as html

log = genutils.log


class base_controller(base.base_obj):

    def __init__(self, idstr: str) -> None:
        """A base class of a controller

        Args:
           idstr: The id of the controller.
        """
        super().__init__(idstr)
        self._lktab: T.Dict[str,
                            T.Callable[[base.base_obj, T.Optional[dict]], None]] = {
                              base.MSGD_BUTTON_CLICK: self.button_press,
                              base.MSGD_LOG_MESSAGE: self.log_event,
                              base.MSGD_FORM_SUBMIT: self.form_submit,
                              base.MSGD_DATA_CACHE_READY: self.data_cache_ready}

    def rcvMsg(self,
               whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: T.Optional[base.MSGdata_Type]) -> None:
        # NOTE: msg can be either a str or a python dct
        whofrom_id = whofrom._idstr or "empty-whofrom"
        log("controller.rcvMsg: RCV({}): '{}' from '{}'".format(self._idstr, msgdesc, whofrom_id))
        handler_method = self._lktab.get(msgdesc, None)
        if handler_method is not None:
            handler_method(whofrom, msgdat)
        else:
            log("controller RCV({}): ignoring msgdesc '{}' from '{}'".format(self._idstr,
                                                                             msgdesc,
                                                                             whofrom_id))
            super().rcvMsg(whofrom, msgdesc, msgdat)

    def button_press(self, whofrom: base.base_obj, data_in: T.Optional[base.MSGdata_Type]) -> None:
        """This function is called when any button is pressed.
        The whofrom_id is a string (the id string, the widget 'idstr' argument) that identifies
        the button.
        """
        pass

    def form_submit(self, whofrom: base.base_obj, data_in: T.Optional[base.MSGdata_Type]) -> None:
        """This function is called when a form has verified its input fields
        and has data to provide. This is sent in the data_in argument.

        Args:
           whofrom: who the message is from
           data_in: the data in the message
        """
        pass

    def data_cache_ready(self, whofrom: base.base_obj, data_in: T.Optional[base.MSGdata_Type]) -> None:
        """ This method is called whenever a MSGD_DATA_CACHE_READY message is sent
        to this controller.

        Args:
           whofrom: who the message is from
           data_in: the data in the message

        Note: the data is provided as a python dictionary.
        """
        pass

    def log_event(self, whofrom: base.base_obj, data_in: T.Optional[base.MSGdata_Type]) -> None:
        """ This method is called whenever the datacache issues a logging event.

        Note: the data is provided as a python dictionary with
        'exitcode' and 'errmsg' keys.
        """
        pass


class base_widget(html.div):
    """The base class of all widgets.
    A widget is a visual html element which is associated with a controller.
    """
    def __init__(self, contr: base_controller, parent: 'base_widget',
                 idstr: str, attrdct: dict, jsel) -> None:
        """
        Args:
           contr: the controller with which this widget is associated.
           parent: the visual parent in the DOM hiearchy.
           idstr: the HTML id string of the object
           attrdct: a dictionary of HTML attributes.
           jsel: an optional existing javascript instance
        """
        super().__init__(parent, idstr, attrdct, jsel)
        self._contr = contr
        if contr is not None:
            self.addObserver(contr, base.MSGD_BUTTON_CLICK)


class ColourLed(base_widget):
    """A coloured round LED indicator button.
    When clicked, this element will send a message with its idstr to the controller.

    Note:
       The colours of this element are created by CSS style sheets (assets/css/leds.css).
    """
    RED = 0
    YELLOW = 1
    GREEN = 2
    BLUE = 3

    def __init__(self, contr: base_controller,
                 parent: base_widget, idstr: str, initial_colour=0) -> None:
        """

        Args:
           contr: the controller of the widget
           parent: the DOM parent
           idstr: the id string
           initial_colour: the initial colour of the LED
        """
        # these reflect the names in the css file. The order must reflect the indices
        # define above.
        self.cols = ['led-red', 'led-yellow', 'led-green', 'led-blue']
        self.cnum = initial_colour
        attrdct = {'class': self.cols[self.cnum]}
        super().__init__(contr, parent, idstr, attrdct, None)

    def stepcolour(self):
        """Move to the next colour in the list."""
        self.cnum = (self.cnum + 1) % len(self.cols)
        self.setAttribute('class', self.cols[self.cnum])


class ImageWidget(base_widget):
    """A widget that contains an html.Img element.
    Button click events are sent to the controller.
    """
    def __init__(self, contr: base_controller, parent: base_widget,
                 idstr: str, attrdct: dict, jsel,
                 urlstr: str, altstr: str) -> None:
        attrdct = attrdct or {}
        if 'class' not in attrdct:
            attrdct['class'] = "user-image img-responsive scopicmenuitem-cls"
        # we use idstr as the id of this widget, and create one for the image.
        # That way, any message we produce will have the idstr name that a controller
        # can listen for
        super().__init__(contr, parent, idstr, attrdct, jsel)
        oidstr = "img-widget-{}".format(idstr)
        self._img = html.Img(self, oidstr, urlstr, altstr, attrdct, None)


class base_button(base_widget):
    def __init__(self, contr: base_controller, parent: base_widget,
                 idstr: str, attrdct: dict, jsel) -> None:
        # attrdct = attrdct or {}
        super().__init__(contr, parent, idstr, attrdct, jsel)
        self._butel = html.button(self, "{}-bb".format(idstr), attrdct, jsel)

    def rcvMsg(self, whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: T.Optional[base.MSGdata_Type]) -> None:
        whofrom_id = whofrom._idstr or "empty-whofrom"
        log("basebutton RECV({}): msgdesc {} from {}".format(self._idstr, msgdesc, whofrom_id))
        # self._contr.rcvMsg(self, msg)


class text_button(base_button):
    def __init__(self, contr: base_controller, parent: base_button,
                 idstr: str, attrdct: dict, jsel, button_text: str) -> None:
        super().__init__(contr, parent, idstr, attrdct, jsel)
        html.textnode(self._butel, button_text)


def scodict_table(parent, idstr, attrdct, coltuple, dct_lst, colattr=None) -> html.table:
    """Generate an HTML table from a list of dictionaries.
    """
    tab_el = html.table(parent, idstr, attrdct, None)
    # enter the column headers
    row = html.tr(tab_el, "%s:header_row" % idstr, None, None)
    for col_name in coltuple:
        html.textnode(html.th(row, col_name, colattr, None), col_name)
    for dct in dct_lst:
        row = html.tr(tab_el, "row", None, None)
        for col_name in coltuple:
            dval = dct[col_name]
            html.textnode(html.td(row, col_name, None, None), dval)
    return tab_el


class sorty_button:
    def __init__(self, parent, text):
        pass


class sort_table:
    """Define a table that can sort by columns."""

    def __init__(self, parent: html.base_element, idstr: str, attrdct: dict,
                 coltuple: T.Tuple[str, str, str], dct_lst: T.List[T.Dict[str, str]]) -> None:
        colattr = {'onclick': 'self.doclick()'}
        self._mytab = scodict_table(parent, idstr, attrdct, coltuple, dct_lst, colattr=colattr)
        # header_id = '%s:header_row' % idstr
        # header_row = tt.getElementById(header_id)
        # log("JAMBAA")
        # if header_row is None:
        #    log("OH NO!!!, NO JAMBA!")
        #    return
        # else:
        #    log('JAMBA OK!')
        # new_row = html.tr(tt, header_id)
        # # now fill the new header with clicky buttons
        # for col_name in coltuple:
        #    html.textnode(html.th(new_row, col_name, colattr), col_name)
        # tt.replaceChild(new_row, header_row)

    def doclick(self):
        log("BLA CLICK")


def writelist(parent: html.base_element, idstr: str, attrdct: dict, iterels, ordered=True):
    """Generate a list of items """
    if ordered:
        lst_el: T.Union[html.ol, html.ul] = html.ol(parent, idstr, attrdct, None)
    else:
        lst_el = html.ul(parent, idstr, attrdct, None)
    for elstr, elattr in iterels:
        html.textnode(html.li(lst_el, "", elattr, None), elstr)
    return lst_el


def writeNEWlist(parent: html.base_element,
                 idstr: str,
                 attrdct: dict,
                 iterels: T.List[T.Tuple[T.Type[html.element], dict]],
                 ordered=True) -> html.element:
    """Generate a list of items
    idstr: the id of the list element created.
    attrdct: the attribute dict of the list element.
    iterels: a list of tuples, each containing a classname and an attribute dict.
    The classname is used to instantiate an html object, which is then an element
    in the list being created.
    """
    if ordered:
        lst_el: T.Union[html.ol, html.ul] = html.ol(parent, idstr, attrdct, None)
    else:
        lst_el = html.ul(parent, idstr, attrdct, None)
    for eltype, elattr_dct in iterels:
        elidstr = elattr_dct.get('scoid', None)
        # this is the visible part of the menu element
        elvis = elattr_dct.get('scoelement', None)
        if elidstr is not None and elvis is not None:
            del elattr_dct['scoelement']
            del elattr_dct['scoid']
            # html.textnode(html.li(lst_el, None), elidstr, elattr)
            menu_el = eltype(html.li(lst_el, "", elattr_dct, None), elidstr, elattr_dct, None)
            if isinstance(elvis, str):
                # log('stringy', elvis)
                # its a string: create a text node
                html.textnode(menu_el, elvis)
            elif isinstance(elvis, html.base_element):
                # log('append', elidstr)
                menu_el.appendChild(elvis)
            else:
                log('UNKNOWN MENU TYPE', elidstr)
        else:
            log("skipping, 'scoid' or 'scoelement' in dict")
    return lst_el


class MenuList(base_widget):
    def __init__(self, contr: base_controller,
                 parent: 'base_widget',
                 idstr: str, attrdct: dict, jsel) -> None:
        super().__init__(contr, parent, idstr, attrdct, jsel)
        self.lst_el = html.ul(parent, idstr, attrdct, jsel)

    def addItem(self, menu_itm: html.element) -> html.element:
        """Append an html item to the end of the menu items."""
        menu_itm.addObserver(self, base.MSGD_BUTTON_CLICK)
        self.lst_el.appendChild(menu_itm)
        return menu_itm

    def rcvMsg(self,
               whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: T.Optional[base.MSGdata_Type]) -> None:
        print("menulst: relaying message {}, {}".format(msgdesc, msgdat))
        self.relayMsg(whofrom, msgdesc, msgdat)


class BasicView(base_widget):
    def __init__(self, contr: base_controller,
                 parent: base_widget,
                 idstr: str,
                 attrdct: dict,
                 jsel) -> None:
        super().__init__(contr, parent, idstr, attrdct, jsel)


class SwitchView(base_widget):
    """An html div element that has a list of other div elements.
    Only one of these is visible at any one time, one is able to switch
    between them.

    Note:
    this works by setting and removing the hidden HTML5 attribute
    of the elements.
    This will only work with list elements that support this attribute, such
    as div elements.
    E.g. adding img elements directly to the switchview will NOT work.
    Instead, use a BasicView, as a parent and then add that BasicView to the switchview.
    """
    def __init__(self, contr: base_controller,
                 parent: base_widget,
                 idstr: str,
                 attrdct: dict, jsel) -> None:
        super().__init__(contr, parent, idstr, attrdct, jsel)
        self.view_lst: T.List[BasicView] = []
        self.view_dct: T.Dict[str, BasicView] = {}

    def addView(self, child_el: BasicView, viewname: str):
        """Add a view into the switchview under a given viewname.
        Args:
           child_el: the view to add to this SwitchView
           viewname: the name of the view to add. This should be unique in the
           switchview, but this is not checked.
        """
        self.view_lst.append(child_el)
        self.view_dct[viewname] = child_el
        child_el.addObserver(self, base.MSGD_BUTTON_CLICK)

    def getView(self, numorname) -> T.Optional[BasicView]:
        """find the view which should be 'on', i.e. visible.

        Args:
           numorname: this can be an int or a string.
              if an int, then the n'th view added to the switch view is returned.
              if a string, a dict lookup is performed.

        Returns:
           The view determined, otherwise None
        """
        on_view = None
        if isinstance(numorname, int):
            if 0 <= numorname < len(self.view_lst):
                on_view = self.view_lst[numorname]
        else:
            on_view = self.view_dct.get(numorname, None)
        if on_view is None:
            log("getView error: no element '{}' found (len={}, names={})".format(numorname,
                                                                                 len(self.view_lst),
                                                                                 " ,".join(self.view_dct.keys())))
        return on_view

    def switchTo(self, numorname) -> None:
        """Make element number n (0 is the first) visible and turn all others off.

        Args:
           numorname: an int or string identifying the view,

        Note:
           if n is an invalid value, then we log a complaint, but otherwise
           do nothing. This will result in all elements being hidden.
        """
        on_view = self.getView(numorname)
        if on_view is None:
            return
        for el in self.view_lst:
            el.set_visible(el == on_view)

    def rcvMsg(self,
               whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: T.Optional[base.MSGdata_Type]) -> None:
        """This method calls :py:meth:`switchTo` in response to messages
           received.
        In this way, e.g. a button element can send a message to the SwitchView to
        switch between views in response to user input.
        """
        print("switchview: got message {}, {}".format(msgdesc, msgdat))
        if msgdat is not None:
            cmd = msgdat.get('cmd', None)
            tgt_view_name = msgdat.get('target', None)
            if cmd == 'viewswitch' and tgt_view_name is not None:
                self.switchTo(tgt_view_name)
