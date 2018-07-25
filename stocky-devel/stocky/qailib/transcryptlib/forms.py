# implement client-side forms. I.e. all handling of the forms are in javascript in the browser.

import typing
import qailib.common.base as base
import qailib.transcryptlib.genutils as genutils
import qailib.transcryptlib.htmlelements as htmlelements
# import qailib.transcryptlib.handlebars as handlebars

log = genutils.log


INPUT_TEXT = 'text'
INPUT_PASSWORD = 'password'
INPUT_SUBMIT = "submit"

# NOTE: we set the class attributes in all elements here so that we can style
# them into a tabular form using css. See the file 'style.css' for details


class modaldiv(htmlelements.div):
    """ See here for how to set this up:
    https://www.w3schools.com/w3css/w3css_modal.asp
    """
    _OPN_MSG = 'modalopen'
    _CAN_MSG = 'modalcancel'

    def __init__(self, parent: htmlelements.base_element,
                 idstr: str, headertitle: str,
                 attrdct: dict, headerfooterclass: str) -> None:
        """ Create a modal div element that can be used as a popup.
        The modal popup contains a
        a) header containing text (headertitle) and a cancel button,
        b) div that the user can access with get_content_element() and fill with content
        c) a footer into which error strings can be but.

        headerfooterclass: a class attribute that is used to style the header and footers
        of the modal dialog. A typical value of this would be "w3-teal"
        """
        super().__init__(parent, idstr, attrdct, None)
        self.addClass('w3-modal')
        # the content level div
        tcidstr = "{}TCONT".format(idstr)
        tcattrdct = {'class': 'w3-modal-content'}
        tcont = self.tcont = htmlelements.div(self, tcidstr, tcattrdct, None)
        cont_attrdct = {'class': 'w3-container'}
        # the header containing the cancel button.
        hidstr = "{}HED".format(idstr)
        head = self.head = htmlelements.header(tcont, hidstr, cont_attrdct, None)
        head.addClass(headerfooterclass)
        # the head has a span with the cancel button
        hspan = htmlelements.span(head, "{}SPAN".format(idstr), {}, None)
        but_attrdct = {'class': "w3-button w3-display-topright",
                       '*buttonpressmsg': modaldiv._CAN_MSG}
        xbutton = htmlelements.textbutton(hspan, "{}CANCEL".format(idstr), but_attrdct, "X")
        xbutton.addObserver(self, base.MSGD_BUTTON_CLICK)
        self.h2 = htmlelements.h2text(head, headertitle)
        spin_attrdct = {'class': "w3-display-topmiddle"}
        self.spinner = spinner(hspan, "myspin", spin_attrdct)

        # the div into which the clients will put content
        cidstr = "{}CONT".format(idstr)
        self.cont = htmlelements.div(tcont, cidstr, cont_attrdct, None)
        # the footer
        fidstr = "{}FOOT".format(idstr)
        foot = self.foot = htmlelements.footer(tcont, fidstr, cont_attrdct, None)
        self.foot.addClass(headerfooterclass)
        self.errspan = htmlelements.spanerrortext(foot, "")

    def set_error_text(self, errtext: str) -> None:
        self.errspan.set_text(errtext)

    def set_busy(self, isbusy: bool) -> None:
        self.spinner.set_spin(isbusy)

    def show(self, on: bool) -> None:
        """Show the modal on == False: switch it off """
        if on:
            self._el.style.display = "block"
        else:
            self._el.style.display = "none"

    def get_content_element(self):
        return self.cont

    def get_show_button(self,
                        buttonparent: htmlelements.base_element,
                        buttontext: str) -> htmlelements.button:
        """Generate a button that can be used to open this modal dialog
        The textbutton will appear in the buttonparent, and show the buttontext.
        """
        idstr = "{}but".format(self._idstr)
        attrdct = {'*buttonpressmsg': modaldiv._OPN_MSG,
                   'class': 'w3-button'}
        self.but = but = htmlelements.textbutton(buttonparent, idstr, attrdct, buttontext)
        but.addObserver(self, base.MSGD_BUTTON_CLICK)
        return but

    def rcvMsg(self,
               whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]) -> None:
        if msgdesc == base.MSGD_BUTTON_CLICK:
            print("form GOT BUTTON CLICK {}".format(msgdat))
            if msgdat == modaldiv._OPN_MSG:
                self.show(True)
            elif msgdat == modaldiv._CAN_MSG:
                self.show(False)
            else:
                print("not handling {}".format(msgdat))


class BaseField(htmlelements.div):

    def __init__(self, parent: htmlelements.base_element,
                 fieldid: str, label: str,
                 input_field_type: str) -> None:
        jsel = None
        attrdct = {'class': 'scoformdiv'}
        super().__init__(parent, fieldid, attrdct, jsel)
        self._fieldid = fieldid
        self._labelstr = label
        self._input_field_type = input_field_type

        self.label = self.genlabelfield()
        self.val = self.geninputfield()

    def id(self):
        return self._idstr

    def genlabelfield(self) -> htmlelements.label:
        attrdct = {'class': 'scoformlabel'}
        idstr = "{}LAB".format(self._fieldid)
        labeltxt = self._labelstr
        return htmlelements.label(self, idstr, attrdct, labeltxt, None)

    def geninputfield(self) -> htmlelements.input:
        """Generate an input field of the type specified in input_field_type.
        For a list of all HTML input types, see
        https://www.w3schools.com/tags/tag_input.asp
        """
        attrdct = {'class': 'scoforminput'}
        idstr = "{}VAL".format(self._fieldid)
        return htmlelements.input(self, idstr, self._input_field_type, attrdct, None)

    def getIDvaltuple(self) -> typing.Tuple[str, str]:
        return (self._fieldid, self.val.get_stringval())


class spinner(htmlelements.div):
    """Display a spinner which can rotate in order to display a 'busy' state.
    This code adapted from https://www.w3schools.com/w3css/w3css_animate.asp
    This class depends on font-awesome 4.7.0 for the image, and on w3 css for the
    spinning.
    In order to:
    a) make the spinner disappear, remove the 'fa-spinner' class attribute.
    b) remain visible, but not spin, remove the 'w3-spin' attribute.
    """
    def __init__(self,
                 parent: htmlelements.base_element,
                 idstr: str, attrdct: dict) -> None:
        htmlelements.div.__init__(self, parent, idstr, attrdct, None)
        self.addClass('fa')
        self.addClass('fa-spinner')
        self.setAttribute('style', "font-size:64px")

    def set_visible(self, on: bool) -> None:
        """Make the spinner visible or invisible.
        The default state is on (visible)"""
        if on:
            self.addClass('fa-spinner')
        else:
            self.removeClass('fa-spinner')

    def set_spin(self, on: bool) -> None:
        """Switch the spinning on or off.
        This will only have a visible effect if the element is also on.
        The default state is no spinning.
        """
        if on:
            self.addClass('w3-spin')
        else:
            self.removeClass('w3-spin')


class form(htmlelements.element):

    def __init__(self, parent: htmlelements.base_element,
                 idstr: str,
                 my_popup: modaldiv,
                 attrdct: typing.Optional[dict],
                 jsel) -> None:
        self._mypopup = my_popup
        attrdct = attrdct or {}
        attrdct['class'] = 'scoform'
        htmlelements.generic_element.__init__(self, 'form', parent, idstr, attrdct, jsel)

    def add_submit_button(self, button_txt: str, attrdct: typing.Optional[dict]):
        """Add a submit button to the form. The button will display the
        provided text. and use any other provided attributes.
        """
        self._addEventListener('submit', self._internal_submithandler)
        att_dct = attrdct or {}
        att_dct = {'value': button_txt, 'class': 'button'}
        idstr = "{}SUB".format(self._idstr)
        return htmlelements.input(self, idstr, INPUT_SUBMIT, att_dct, None)

    def _internal_submithandler(self, jsel):
        """This method is called when the user presses the submit button of the form.
        As we are handling the form completely on the client side, we must prevent
        the form from being submitted to the server -- hence the preventDefault() call.
        The user- provided on submit method is then called normally."""
        log("internal submit {}".format(self._idstr))
        jsel.preventDefault()
        self._mypopup.set_error_text(" ")
        self.on_submit()

    def on_submit(self):
        """This routine is called whenever the submit button is pressed.
        It may be overridden in lower classes."""
        log("form.on_submit!! (should this be overridden?) {}".format(id))

    def submit(self):
        "This is for testing. It creates a submit event in software"
        self._el.submit()


class loginform(form):
    def __init__(self, parent: htmlelements.base_element,
                 idstr: str,
                 my_popup: modaldiv,
                 attrdct: typing.Optional[dict]) -> None:
        form.__init__(self, parent, idstr, my_popup, attrdct, None)
        self.username = BaseField(self, 'username', 'User Name', INPUT_TEXT)
        self.password = BaseField(self, 'password', 'Password', INPUT_PASSWORD)
        self.add_submit_button("Login in", None)

    def on_submit(self):
        """This method is envoked when the 'Login In' submit button is pressed."""

        popup = self._mypopup
        popup.set_busy(True)
        untup = self.username.getIDvaltuple()
        pwtup = self.password.getIDvaltuple()
        print("UN {}".format(untup))
        print("PW {}".format(pwtup))
        # perform some very simple error checking...
        uname = untup[1]
        pword = pwtup[1]
        if uname == "" or pword == "":
            popup.set_error_text("user name and/or password is empty")
            popup.set_busy(False)
        else:
            # pass the information along...
            dct = {untup[0]: untup[1], pwtup[0]: pwtup[1]}
            self.sndMsg(base.MSGD_FORM_SUBMIT, dct)

    def set_login_response(self, resdct: dict):
        """Respond visually to a login attempt """
        popup = self._mypopup
        popup.set_busy(False)
        is_logged_in = resdct['ok']
        if is_logged_in:
            # success: remove the modal
            popup.show(False)
        else:
            # display the error message
            popup.set_error_text(resdct['msg'])
