
# python overlay of DOM objects
# implement things from here
# https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement

import typing
from org.transcrypt.stubs.browser import document


import qailib.common.base as base


class selfmapper:
    def __init__(self):
        self._dct = {}
        self._ptrnum = 1000

    def add_self(self, self_ptr):
        self_str = "PTR{}".format(self._ptrnum)
        self._dct[self_str] = self_ptr
        self._ptrnum += 1
        return self_str

    def get_self(self, self_string):
        """ Return the self pointer or None if none is found."""
        return self._dct.get(self_string, None)


_mm = selfmapper()


def setCursorBusy(on: bool) -> None:
    """Set the cursor to busy (wait) on or off"""
    if on:
        document.body.style.cursor = 'wait'
    else:
        document.body.style.cursor = 'auto'


def getJsElementById(idstr: str):
    return document.getElementById(idstr)


def getPyElementByJsEl(idstr: str,
                       jsel,
                       classname,
                       attrdct: typing.Optional[dict]) -> "base_element":
    """Return a python instance of a designated class classname"""
    py_obj = _mm.get_self(jsel.getAttribute('scoself'))
    py_obj = py_obj or classname(None, idstr, attrdct, jsel)
    return py_obj


def getPyElementById(idstr: str) -> typing.Optional["base_element"]:
    """Return a python element of the document element... Return None iff none found
    """
    jsel_found = document.getElementById(idstr)
    if jsel_found is None:
        return None
    # now determine the scoself object if we have one, otherwise create a new python object for it.
    py_obj = _mm.get_self(jsel_found.getAttribute('scoself'))
    py_obj = py_obj or base_element(jsel_found, idstr)
    return py_obj


def getPyElementByIdClass(idstr: str, classname, attrdct: dict) -> typing.Optional["base_element"]:
    """Return a python element given the id string of an HTML element.
    Return a new python class of class classname that wraps the HTML element.
    Return None if no existing js element with the idsr is found.

    NOTE: we do not check whether the existing HTML element is of the same
    type as the desired python object; i.e. there is nothing to stop
    a caller from creating an html.a object for a predefined HTML select object.
    """
    jsel_found = document.getElementById(idstr)
    if jsel_found is None:
        return None
    # now determine the scoself object if we have one, otherwise create a new python object for it.
    return getPyElementByJsEl(idstr, jsel_found, classname, attrdct)


class base_element(base.base_obj):
    """A class that wraps a javascript html element.
    Each instance also has a unique id string.
    """

    # predefined special attributes that start with a '*'
    # see generic_element for an example of how this is used.
    STARATTR_ONCLICK = '*buttonpressmsg'

    def __init__(self, jsel, idstr: str) -> None:
        super().__init__(idstr)
        self._el = jsel
        self.setAttribute('scoself', _mm.add_self(self))
        if idstr is not None:
            self.setAttribute('id', idstr)

    def setAttribute(self, k: str, v) -> None:
        self._el.setAttribute(k, v)

    def getAttribute(self, k: str) -> str:
        return self._el.getAttribute(k)

    def removeAttribute(self, k: str) -> None:
        self._el.removeAttribute(k)

    def hasAttribute(self, k: str) -> bool:
        return self._el.hasAttribute(k)

    def getID(self) -> str:
        """Short form of self.getAttribute('id')"""
        return self._el.getAttribute("id")

    def getNodeName(self) -> str:
        """Return the javascript elements nodeName string.
        This is an upper-case description of the html tag, e.g. 'DIV', 'SPAN'
        """
        return self._el.nodeName

    # child manipulation
    def appendChild(self, child: "base_element") -> None:
        self._el.appendChild(child._el)

    def removeChild(self, child: "base_element") -> None:
        """Remove a child from this element"""
        self._el.removeChild(child._el)

    def replaceChild(self, new_child: "base_element", old_child: "base_element") -> None:
        self._el.replaceChild(new_child._el, old_child._el)

    def setInnerHTML(self, newhtml: str) -> None:
        """Set this element's innerHTML contents to the provided HTML string"""
        self._el.innerHTML = newhtml

    def getInnerHTML(self) -> str:
        """Return this element's innerHTML contents as a string"""
        return self._el.innerHTML

    def get_WH(self) -> typing.Tuple[int, int]:
        """Return the width and height of the element in pixels."""
        rc = self._el.getBoundingClientRect()
        return (rc.width, rc.height)

    # manipulate class attributes
    # see https://developer.mozilla.org/en-US/docs/Web/API/Element/classList for
    # how these work.
    def addClass(self, cls_name: str) -> None:
        """Add a new class value. If the value exists already, then nothing is done."""
        self._el.classList.add(cls_name)

    def removeClass(self, cls_name: str) -> None:
        self._el.classList.remove(cls_name)

    def toggleClass(self, cls_name: str) -> bool:
        return self._el.classList.toggle(cls_name)

    def toggleForceClass(self, cls_name: str, force: bool) -> bool:
        return self._el.classList.toggle(cls_name, force)

    def containsClass(self, cls_name: str) -> bool:
        return self._el.classList.contains(cls_name)

    def replaceClass(self, oldcls_name: str, newcls_name: str) -> None:
        self._el.classList.replace(oldcls_name, newcls_name)


# my_handles=set(['onclick'])

class textnode(base_element):
    def __init__(self, parent: base_element, text: str) -> None:
        text = text or ""
        self._el = document.createTextNode(text)
        if parent is not None:
            parent.appendChild(self)

    def set_text(self, newtext: str) -> None:
        self._el.nodeValue = newtext
        # print("newtextset to '{}'".format(newtext))


def create_elementstring(parent: base_element, idstr: str, attrdct: dict,
                         elementclass, text: str) -> "element":
    """Helper function to create a specified HTML element of class 'elementclass'
    with a textnode in it.
    The element created is returned.
    Example of use:
    title_el = html.create_elementstring(view, 'dashtitle', None,
                                         html.h1, "User Dashboard")
    This creates an html.h1 element in the provided view with the text 'User Dashboard'
    """
    el = elementclass(parent, idstr, attrdct)
    textnode(el, text)
    return el


class generic_element(base_element):
    def __init__(self,
                 tagname: str,
                 parent: base_element,
                 idstr: str,
                 attrdct: typing.Optional[dict],
                 jsel) -> None:
        """Add an HTML element of type tagname to the parent. The new element
        will have an idstr and certain additional attributes as defined in attrdct.

        tagname: the kind of html tag to create (e.g. 'p', or 'h1')
        parent: the newly created element is placed under the parent.
        If this is None, the element is created in the
        document.body (i.e. globally in the document)
        idstr: a string identifying the object.
        If this is None, no id attribute is set.
        NOTE: this string, if provided, should be unique within the scope of the complete
        document in order to be uniquely found.
        attrdct: a dictionary of HTML attributes to set. The exact attributes
        allowed will depend on the element type.
        There are additional keys of the attrdct which are recognised by this class
        and kept in a separate directory for later use. These reserved keyword attributes
        are not used as html attributes.
        A reserved attribute is recognised because its name starts with a star '*'.
        For example, *buttonpressmsg is a locally reserved attribute.

        jsel: The HTML dom object to wrap around. If this is not provided,
        a new object is created in the document.
        NOTE: if jsel IS provided, then the place of the existing element in the DOM hierarchy
        is NOT modified and no addObserver calls are issued.
        In other words, the parent argument is ignored.
        """
        do_create = jsel is None
        if do_create:
            jsel = document.createElement(tagname)
        super().__init__(jsel, idstr)
        self._locattrdct: dict = {}
        did_add_onclick = False
        if attrdct is not None:
            for k, v in attrdct.items():
                if k.startswith('*'):
                    self._locattrdct[k] = v
                else:
                    self.setAttribute(k, v)
            did_add_onclick = 'onclick' in attrdct
            # print('element: ADDING default onclick for {}'.format(idstr))
            # self._el.onclick = self._clickfunc
        self._parent: typing.Optional[base_element] = None
        if do_create:
            if parent is self:
                print("BIG ERROR: self == parent!")
            if parent is None:
                document.body.appendChild(self._el)
            else:
                parent.appendChild(self)
                self.addObserver(parent, base.MSGD_DEFAULT)
                self._parent = parent
        if not did_add_onclick:
            self._el.addEventListener("click", self._clickfunc, False)

    def _clickfunc(self):
        msgdat = self._locattrdct.get(base_element.STARATTR_ONCLICK, None)
        if msgdat is not None:
            print("element._clickfunc: '{}' creating onclick event".format(self._idstr))
            self.sndMsg(base.MSGD_BUTTON_CLICK, msgdat)
        else:
            print("element._clickfunc: '{}': got None, ignoring event".format(self._idstr))

    def _addEventListener(self, event_name: str, cbfunc) -> None:
        # self._el.addEventListener("click", self._clickfunc, False)
        self._el.addEventListener(event_name, cbfunc, False)

    def setAttribute(self, k: str, v) -> None:
        if k.startswith('*'):
            self._locattrdct[k] = v
        else:
            self._el.setAttribute(k, v)

    def getAttribute(self, k: str) -> str:
        if k.startswith('*'):
            return self._locattrdct.get(k, None)
        else:
            return self._el.getAttribute(k)

    def removeAttribute(self, k: str) -> None:
        if k.startswith('*'):
            if k in self._locattrdct:
                del self._locattrdct[k]
        else:
            self._el.removeAttribute(k)

    def hasAttribute(self, k: str) -> bool:
        if k.startswith('*'):
            return self._locattrdct.get(k, None) is not None
        else:
            return self._el.hasAttribute(k)

    def rcvMsg(self, whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]):
        """Unless overridden, every object simply passes on a message to its parent"""
        print("element.RECV({}): msg {} from {}: passing to parent..".format(self._idstr, msgdesc, whofrom._idstr))
        if self._parent is not None:
            self._parent.rcvMsg(whofrom, msgdesc, msgdat)


class element(generic_element):
    """A virtual basic html element class. This class exists solely so that all actual
    html elements such as buttons etc., have one common base type.
    The __init__ method of any derived classes must call generic_element.__init__()
    instead of simply super()...
    """
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        pass


class button(element):
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'button', parent, idstr, attrdct, jsel)


class textbutton(button):
    """A predefined button with text content"""
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, buttontext: str) -> None:
        button.__init__(self, parent, idstr, attrdct, None)
        self._textnode = textnode(self, buttontext)


class h1(element):
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'h1', parent, idstr, attrdct, jsel)


class h2(element):
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'h2', parent, idstr, attrdct, jsel)


class h1text(h2):
    """A predefined h2 text element."""
    def __init__(self, parent: base_element, h1text: str) -> None:
        idstr = ""
        # NOTE: 2018-07-24: for some reason, cannot use super() here --> javascript error.
        h1.__init__(self, parent, idstr, {}, None)
        self._textnode = textnode(self, h1text)


class h2text(h2):
    """A predefined h2 text element."""
    def __init__(self, parent: base_element, h2text: str) -> None:
        idstr = ""
        # NOTE: 2018-07-24: for some reason, cannot use super() here --> javascript error.
        h2.__init__(self, parent, idstr, {}, None)
        self._textnode = textnode(self, h2text)


class h3(element):
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'h3', parent, idstr, attrdct, jsel)


class p(element):
    """A paragraph element."""
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'p', parent, idstr, attrdct, jsel)


class div(element):
    """A div element."""

    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'div', parent, idstr, attrdct, jsel)


class span(element):
    """A span element."""
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'span', parent, idstr, attrdct, jsel)


class header(element):
    """A header element."""
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'header', parent, idstr, attrdct, jsel)


class footer(element):
    """A footer element."""
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'footer', parent, idstr, attrdct, jsel)


class spantext(element):
    """A predefined span element used to display text in forms.
    The visual appearance of the text is determined by HTML style
    sheets (the html class is set to attrclass.
    """
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, text: str) -> None:
        generic_element.__init__(self, 'span', parent, idstr, attrdct, None)
        self._textnode = textnode(self, text)

    def set_text(self, newtext: str) -> None:
        self._textnode.set_text(newtext)


class spanhelptext(spantext):
    """A predefined span element used to display help text in forms.
    The visual appearance of the text is determined by HTML style
    sheets (the html class is set to 'helptext').
    """
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, helptext: str) -> None:
        super().__init__(parent, idstr, attrdct, helptext)
        self.addClass('helptext')


class spanerrortext(spantext):
    """A predefined span element used to display error text in forms.
    The visual appearance of the text is determined by HTML style
    sheets (the html class is set to 'w3-pink').
    """
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, errtext: str) -> None:
        super().__init__(parent, idstr, attrdct, errtext)
        self.addClass('w3-pink')


class a(element):
    """A link element.
    NOTE: set the href attribute in attrdct for the link destination.
    """
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'a', parent, idstr, attrdct, jsel)


class img(element):
    """An image element.
    https://www.w3schools.com/html/html_images.asp
    Set the following attributes:
    src    with image URL,
    alt    text to display when no image can be displayed
    style  describe height, and width OR alternatively, set
    width height  attributes directly.
    """

    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'img', parent, idstr, attrdct, jsel)


class Img(img):
    def __init__(self, parent: base_element, idstr: str,
                 urlstr: str, altstr: str, attrdct: dict, jsel) -> None:
        attrdct = attrdct or {}
        attrdct['src'] = urlstr
        attrdct['alt'] = altstr
        super().__init__(parent, idstr, attrdct, jsel)


# tables and table elements
class table(element):
    """A table element. With the appropriate HTML definitions, clicking on the
    table headers will sort according to that column.
    """

    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'table', parent, idstr, attrdct, jsel)
        self.sort_colnum = None
        self._header_cells: typing.Optional[list] = None
        for colnum, pyth in enumerate(self.get_header_cells()):
            pyth.setAttribute(base_element.STARATTR_ONCLICK, {'cmd': 'tablesort',
                                                              'colnum': colnum})
            pyth.addObserver(self, base.MSGD_BUTTON_CLICK)

    def get_header_cells(self) -> list:
        if self._header_cells is None:
            jsrow, rownum = self._el.rows[0], 0
            idstub = self.getID()
            pyrow = typing.cast(tr, getPyElementByJsEl("{}{}".format(idstub, rownum),
                                                       jsrow,
                                                       tr,
                                                       None))
            if pyrow is None:
                print("columnsort: pyrow is None")
                return
            self._header_cells = pyrow.getcells()
        return self._header_cells

    def getrows(self) -> typing.List['tr']:
        """Return a list of python tr objects from the HTML-defined table.
        New python objects are created if they do not already exist.
        """
        idstub = self.getID()
        return [typing.cast(tr, getPyElementByJsEl("{}{}".format(idstub, rownum),
                                                   jsrow,
                                                   tr,
                                                   None)) for jsrow, rownum in enumerate(self._el.rows)]

    def columnsort(self, colnum: int) -> None:
        """Sort the rows of the table using the javascript onclick() attributes
        in the header row.
        NOTE: if these atrributes are not set, this will fail.
        """
        hc = self.get_header_cells()
        if colnum >= len(hc):
            print("illegal sort colnum {} {}".format(colnum, len(hc)))
            return
        hc[colnum]._el.onclick()

    def rcvMsg(self, whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]) -> None:
        if msgdesc == base.MSGD_BUTTON_CLICK:
            print("table GOT BUTTON CLICK")
            if msgdat is None:
                print("msgdat is None")
                return
            cmd = msgdat.get("cmd", None)
            print("table GOT BUTTON CLICK CMD {}".format(cmd))
            if cmd == 'tablesort':
                colnum = msgdat.get("colnum", None)
                print("GOT table sort colnum {}".format(colnum))
                self.sort_colnum = colnum
            else:
                print('webclient: unrecognised cmd')
                return


class tr(element):
    """A table row element"""

    def __init__(self, parent: base_element,
                 idstr: str,
                 attrdct: typing.Optional[dict],
                 jsel) -> None:
        generic_element.__init__(self, 'tr', parent, idstr, attrdct, jsel)

    def getcells(self) -> list:
        """Return a list of cells (th or td elements) in this row as python objects.
        New python objects are created if they do not already exist.
        idstup is used to generate idstrings for the newly created objects
        if the objects do not already have ids.
        """
        idstub = self.getID()
        retlst, rownum = [], 0
        for jscell in self._el.cells:
            nn = jscell.nodeName
            if nn == 'TD':
                cell = getPyElementByJsEl("{}{}".format(idstub, rownum),
                                          jscell,
                                          td,
                                          None)
                retlst.append(cell)
                rownum += 1
            elif nn == 'TH':
                cell = getPyElementByJsEl("{}{}".format(idstub, rownum),
                                          jscell,
                                          th,
                                          None)
                retlst.append(cell)
                rownum += 1
            else:
                print('getcells: unexpected nodename {}'.format(nn))
        return retlst


class th(element):
    """A table header element"""

    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'th', parent, idstr, attrdct, jsel)


class td(element):
    """A table data cell element"""

    def __init__(self, parent: base_element, idstr: str, attrdct: typing.Optional[dict], jsel) -> None:
        generic_element.__init__(self, 'td', parent, idstr, attrdct, jsel)


# orders and unordered lists, and list items
class ol(element):
    """An ordered list of li items"""

    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'ol', parent, idstr, attrdct, jsel)


class ul(element):
    """An unordered list (bullet list) of list items"""

    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'ul', parent, idstr, attrdct, jsel)


class li(element):
    """A list item element"""

    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'li', parent, idstr, attrdct, jsel)


class label(element):
    """A label element"""

    def __init__(self,
                 parent: base_element,
                 idstr: str,
                 attrdct: dict,
                 labeltext: str,
                 jsel) -> None:
        generic_element.__init__(self, 'label', parent, idstr, attrdct, jsel)
        self.setInnerHTML(labeltext)


class select(element):
    """A select element"""

    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'select', parent, idstr, attrdct, jsel)

    def get_selected(self) -> typing.Tuple[int, str]:
        """Return the currently selected index and value string """
        sel_ndx = self._el.selectedIndex
        val = self._el.options[sel_ndx].value
        return (int(sel_ndx), val)


class input(element):
    def __init__(self, parent: base_element, idstr: str,
                 inp_type: str, attrdct: dict, jsel) -> None:
        """Create a new input HTML element.
        inp_type: one of the HTML-defined input types e.g. 'button', 'checkbox' etc.
        https://www.w3schools.com/tags/tag_input.asp
        """
        if attrdct is None:
            attrdct = {'type': inp_type}
        else:
            attrdct['type'] = inp_type
        generic_element.__init__(self, 'input', parent, idstr, attrdct, jsel)

    def get_stringval(self) -> str:
        return self._el.value

    def set_stringval(self, newstr: str) -> None:
        self._el.value = newstr

    def getIDvaltuple(self) -> typing.Tuple[str, str]:
        # self.getAttribute('value'), always return the
        # INITIAL value; It does not return the current value that the user has entered into
        # the input element: We must access by javascript .value
        return (self.getAttribute('id'), self._el.value)


class input_list(input):
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        self.idstr = idstr
        # super().__init__(parent, idstr, 'button', attrdct)
        generic_element.__init__(self, 'div', parent, idstr, attrdct, jsel)
        self._ellst: typing.List[input] = []

    def addItem(self, el: input) -> None:
        self._ellst.append(el)

    def getIDvaltuple(self) -> typing.Tuple[str, str]:
        idstr = self.idstr
        retlst = [el.getIDvaltuple() for el in self._ellst]
        return (idstr, str(retlst))


class input_button(input):
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        super().__init__(parent, idstr, 'button', attrdct, jsel)


class input_submit(input):
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        super().__init__(parent, idstr, 'submit', attrdct, jsel)


class LEDElement(div):
    """A coloured round LED indicator button.
    NOTE: the colours of this element are created by CSS style sheets (assets/css/leds.css).
    """
    RED = 0
    YELLOW = 1
    GREEN = 2
    BLUE = 3

    def __init__(self, parent: base_element,
                 idstr: str,
                 attrdct: dict,
                 jsel,
                 initial_colour: int=0) -> None:
        # these reflect the names in the css file. The order must reflect the indices
        # defined above.
        self.cols = ['led-red', 'led-yellow', 'led-green', 'led-blue']
        self.cnum = initial_colour
        attrdct = attrdct or {}
        attrdct['class'] = self.cols[self.cnum]
        super().__init__(parent, idstr, attrdct, jsel)

    def setcolour(self, newcol: int) -> None:
        """Set the LED to the colour indicated. newcol must be one of the constants
        defined above.
        """
        self.cnum = (newcol % len(self.cols))
        self.setAttribute('class', self.cols[self.cnum])

    def stepcolour(self):
        """Move to the next colour in the list."""
        self.cnum = (self.cnum + 1) % len(self.cols)
        self.setAttribute('class', self.cols[self.cnum])
