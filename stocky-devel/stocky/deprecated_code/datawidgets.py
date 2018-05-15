

from org.transcrypt.stubs.browser import FormData, __new__
import qailib.common.serversocketbase as serversocketbase
import qailib.common.dataelements as dataelements
import qailib.transcryptlib.guiforms as guiforms


class socket_controller(base_controller):
    """The base class of all main programs on the client side.
    The controller uses a server_socket to communicate with the server via
    a data_cache, and responds to events received.
    """
    def __init__(self, myname: str, ws: serversocketbase.base_server_socket) -> None:
        super().__init__(myname)
        self._ws = ws
        self._dcache = dataelements.data_cache("datacache", ws)
        self._dcache.addObserver(self, base.MSGD_LOG_MESSAGE)
        self._dcache.addObserver(self, base.MSGD_DATA_CACHE_READY)

        # NOTE: server messages are sent to the datacache
        # ws.addObserver(self, base.MSGD_SERVER_MSG)


class FormWidget(base_widget):
    """A Basic Form widget.
    Note that, in 'normal' http-based web sites, the form HTML element has
    an 'action' attribute (URL on the server to which the form data
    is sent)
    and a 'method' attribute (PUT or GET http method).
    Here, however, we are using websockets to communicate with the server, and we must
    therefore NOT allow the form to be submitted in the conventional sense.
    There are at least two ways of doing this:
    a) use a submit input element and override the onsubmit method of the form
    b) use button input element and override the onclick method of the form.
    As the messaging system already uses B, we opt for that.

    Note that in addition, catching the onsubmit events would require called javascript
    calls ev.preventDefault() and ev.stopPropagation() in the event handler.
    """
    def __init__(self,
                 contr: base_controller,
                 parent: 'base_widget',
                 idstr: str,
                 attrdct: dict,
                 jsel,
                 formbuilder: guiforms.HtmlFormBuilder,
                 my_user_data: dataelements.record) -> None:
        super().__init__(contr, parent, "{}-pp".format(idstr), attrdct, jsel)
        self._formbuilder = formbuilder
        self._userdata = my_user_data
        self.form_el = html.form(self, idstr, None, None)
        html_tab, self._field_lst = formbuilder.gen_table(self.form_el,
                                                          'usertable',
                                                          dict(border=1, width='100%'),
                                                          my_user_data)
        self.addItem(html_tab)
        self.addSubmitButton('usermod-button', 'Submit')
        self.addObserver(contr, base.MSGD_FORM_SUBMIT)

    def addItem(self, menu_itm: html.element) -> html.element:
        """Append an html item to the end of the form elements."""
        self.form_el.appendChild(menu_itm)
        return menu_itm

    def addSubmitButton(self, button_idstr: str, buttontext: str) -> None:
        attrdct = {"value": buttontext, "type": "submit"}
        self.button = html.input_button(self.form_el, button_idstr, attrdct, None)
        # self.button._el.onsubmit = self._onsubmit
        self.button.addObserver(self, base.MSGD_BUTTON_CLICK)

    def rcvMsg(self,
               whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: Optional[base.MSGdata_Type]) -> None:
        if whofrom == self.button:
            print("FormWidget received my button click!")
            # this doesn't seem to exist...
            # self.handle_submission()
        else:
            print("menulst: relaying message {}, {}".format(msgdesc, msgdat))
            self.relayMsg(whofrom, msgdesc, msgdat)

    def OLDgetFormData(self) -> dict:
        """Return a dict containing the current values of the form elements.
        This method reaches into the nether regions of javascript and uses
        a FormData element to retrieve the keys and values of any input elements
        in the form.
        See here for the specification of FormData:
        https://developer.mozilla.org/en-US/docs/Web/API/FormData/Using_FormData_Objects

        NOTE: this should work, and it did use to; However now it returns an empty
        string. We work around this by extracting the data from the form ourselves.
        """
        fd = __new__(FormData(self.form_el._el))
        return dict([tt for tt in fd.entries()])


