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

    def __init__(self, parent: htmlelements.base_element,
                 idstr: str, attrdct: dict, jsel) -> None:
        attrdct = attrdct or {}
        attrdct = {'class': 'w3-modal'}
        super().__init__(parent, idstr, attrdct, jsel)

        # the content level div
        cidstr = "{}CONT".format(idstr)
        cattrdct = {'class': 'w3-modal-content'}
        self.cont = htmlelements.div(self, cidstr, cattrdct, None)

    def show(self, on: bool) -> None:
        """Show the modal on == False: switch it off """
        if on:
            self._el.style.display = "block"
        else:
            self._el.style.display = "none"

    def get_content_element(self):
        return self.cont

    def showit(self):
        self.show(True)

    def get_show_button(self,
                        buttonparent: htmlelements.base_element,
                        buttontext: str) -> htmlelements.button:
        idstr = "{}but".format(self._idstr)
        attrdct = {'*buttonpressmsg': 'modalopen',
                   'class': 'w3-button'}
        self.but = but = htmlelements.button(buttonparent, idstr, attrdct, None)
        htmlelements.textnode(but, buttontext)
        but.addObserver(self, base.MSGD_BUTTON_CLICK)
        return but

    def rcvMsg(self,
               whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]) -> None:
        if msgdesc == base.MSGD_BUTTON_CLICK:
            print("form GOT BUTTON CLICK")
            self.show(True)


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


class form(htmlelements.element):

    def __init__(self, parent: htmlelements.base_element,
                 idstr: str,
                 attrdct: typing.Optional[dict],
                 jsel) -> None:
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
        log("SCOSUBMIT!!! {}".format(self._idstr))
        jsel.preventDefault()
        self.on_submit()

    def on_submit(self):
        """This routine is called whenever the submit button is pressed.
        It may be overridden in lower classes."""
        log("SUBMIIIT {}".format(id))

    def submit(self):
        self._el.submit()


class loginform(form):
    def __init__(self, parent: htmlelements.base_element,
                 idstr: str,
                 attrdct: typing.Optional[dict]) -> None:
        form.__init__(self, parent, idstr, attrdct, None)
        self.username = BaseField(self, 'username', 'User Name', INPUT_TEXT)
        self.password = BaseField(self, 'password', 'Password', INPUT_PASSWORD)

        self.add_submit_button("Login in", None)

    def on_submit(self):
        print("UN {}".format(self.username.getIDvaltuple()))
        print("PW {}".format(self.password.getIDvaltuple()))
