"""A python overlay of HTML DOM objects as defined
   here: https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement
"""
import typing
from org.transcrypt.stubs.browser import document, alert


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
    """Return a python instance of a designated class classname.
    If a python instance of the given js element with the provided idstr exists
    already, this is returned.
    Otherwise, a new object of the specified class is created.

    Args:
       idstr: the name of the instance to be created
       jsel: the javascript object that this object mirrors.
       classname: the classname of the python instance that should be returned.
       attrdct: the HTML attribute dict to use for the HTML object.

    Returns:
       The created python object.
    """
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
    """Return a python element given the id string of an existing HTML element.

    Args:
       idstr: the idstr of the HTML element existing in the DOM.
       classname: the class of the instance to create
       attrdct: the attribute dict of the newly created instance.

    Returns:
       A new python class of class classname that wraps the HTML element.
       None if no existing js element with the idstr is found.
    Note:
       We do not check whether the existing HTML element is of the same
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
    STARATTR_ONCHANGE = '*onchangemsg'

    def __init__(self, jsel, idstr: str) -> None:
        """
        Args:
           jsel: the javascript object that this instance is mirroring.
           idstr: the id string of this instance.
        """
        super().__init__(idstr)
        self._el = jsel
        self.setAttribute('scoself', _mm.add_self(self))
        if idstr is not None:
            self.setAttribute('id', idstr)

    def setAttribute(self, k: str, v: str) -> None:
        """Set the HTML attribute k to value v.

        Args:
           k: the name of the attribute to set.
           v: the value to set the attribute to.
        """
        self._el.setAttribute(k, v)

    def getAttribute(self, k: str) -> typing.Optional[str]:
        """Retrieve the value of the attribute k.

        Args:
           k: the name of the attribute, the value of which is retrieved.

        Returns:
           the value of the attribute or None if no attribute of the name k exists.
        """
        return self._el.getAttribute(k)

    def removeAttribute(self, k: str) -> None:
        """Remove the attribute with the name k.

        Args:
           k: the name of the attribute to remove.
        """
        self._el.removeAttribute(k)

    def hasAttribute(self, k: str) -> bool:
        """
        Args:
           k: the name of the attribute

        Returns:
           the element has attribute called k
        """
        return self._el.hasAttribute(k)

    def set_visible(self, is_visible: bool) -> None:
        """Set this element to be hidden or visible.
        Initially, upon creation, all elements are visible.

        Args:
           is_visible: True switches the element on, i.e. visible.
        Note:
           This routine is implemented by setting/unsetting of the
           'hidden' HTML attribute. It is possible, to set this directly.
        """
        if is_visible:
            self.removeAttribute('hidden')
        else:
            self.setAttribute('hidden', 'true')

    def getID(self) -> str:
        """
        Returns:
           The id of this instance.
        Note:
           This is a short form of self.getAttribute('id')
        """
        return self._el.getAttribute("id")

    def getNodeName(self) -> str:
        """Return the javascript elements nodeName string.

        Returns:
           The name of HTML node name. This is an upper-case description of the
           html tag, e.g. 'DIV', 'SPAN'.
        """
        return self._el.nodeName

    # child manipulation
    def appendChild(self, child: "base_element") -> None:
        """Add a child to this element.

        Args:
           child: the python object to add as a child.

        Note:
           It is assumed that the python object also has a javascript element. Appending
           only happens between the javascript objects. No linking
           between the python objects is performed.
        """
        self._el.appendChild(child._el)

    def removeChild(self, child: "base_element") -> None:
        """Remove a child from this element.

        Args:
           child: The python instance to remove from this instance.

        Note:
           The operation is performed at the level of the javascript elements.
        """
        self._el.removeChild(child._el)

    def replaceChild(self, new_child: "base_element", old_child: "base_element") -> None:
        """Replace an existing python child element with another.

        Args:
           new_child: the new child object
           old_child: the python child object to be replaced.
        Note:
           The operation is performed at the level of the javascript elements.
        """
        self._el.replaceChild(new_child._el, old_child._el)

    def setInnerHTML(self, newhtml: str) -> None:
        """Set this element's innerHTML contents to the provided HTML string

        Args:
           newhtml: the new HTML contents in string form.
        """
        self._el.innerHTML = newhtml

    def getInnerHTML(self) -> str:
        """
        Returns:
           This element's innerHTML contents as a string
        """
        return self._el.innerHTML

    def removeAllChildren(self) -> None:
        """Remove all javascript elements from this instance.

        Note:
           The operation is performed at the level of the javascript elements.
        """
        jsel = self._el
        while jsel.firstChild:
            jsel.removeChild(jsel.firstChild)

    def get_WH(self) -> typing.Tuple[int, int]:
        """Return the width and height of the element in pixels.

        Returns:
           the (width, height) of this element in pixels.
        """
        rc = self._el.getBoundingClientRect()
        return (rc.width, rc.height)

    def addClass(self, cls_name: str) -> None:
        """Add a new class value.

        Args:
           cls_name: the class name to add. If the value exists already,\
           then nothing is done.

        Note:
           See https://developer.mozilla.org/en-US/docs/Web/API/Element/classList for
           how to manipulate class attributes.
        """
        self._el.classList.add(cls_name)

    def removeClass(self, cls_name: str) -> None:
        """Remove class attribute.

        Args:
           cls_name: the class name to remove
        """
        self._el.classList.remove(cls_name)

    def toggleClass(self, cls_name: str) -> bool:
        """Toggle a class attribute, i.e. if it already exists, it is removed.
        If it does not exist, it is added.

        Args:
           cls_name: the class name to toggle.
        """
        return self._el.classList.toggle(cls_name)

    def toggleForceClass(self, cls_name: str, force: bool) -> bool:
        return self._el.classList.toggle(cls_name, force)

    def containsClass(self, cls_name: str) -> bool:
        """Determine whether this instance contains a class attribute.

        Args:
           cls_name: the name of the class attribute to query.
        """
        return self._el.classList.contains(cls_name)

    def replaceClass(self, oldcls_name: str, newcls_name: str) -> None:
        """Replace a class attribute with another.

        Args:
           oldcls_name: the class name to be removed
           newcls_name: the class name to be added.
        """
        self._el.classList.replace(oldcls_name, newcls_name)

    def add_attrdct(self, attrdct: dict) -> None:
        """Add all attributes in this dict to this instance.

        Args:
           attrdct: k, v of attribute name, value pairs.

        Note:
           The key 'class', if present, is treated differently from other attributes:
           its value is assumed to consist of a string consisting of space-separated classnames.
           These are classnames are added by calling self.addClass(classname)
        """
        for k, v in attrdct.items():
            if k == 'class':
                for cn in v.split():
                    self.addClass(cn)
            else:
                self.setAttribute(k, v)

    def rem_attrdct(self, attrdct: dict) -> None:
        """Try to set all of the attributes in the dict.

        Args:
           attrdct: k, v of attribute name, value pairs to remove.
           The values v are ignored when removing attributes, **except**
           when the attribute name k is 'class'.
           In this case, the corresponding value is assumed to consist of a string with
           space-separated class names. These class names are removed by calling
           self.removeClass(classname)
        """
        for k, v in attrdct.items():
            if k == 'class':
                for cn in v.split():
                    self.removeClass(cn)
            else:
                self.removeAttribute(k)

# my_handles=set(['onclick'])


class textnode(base_element):
    """A base element with an HTML textnode."""

    def __init__(self, parent: base_element, text: str) -> None:
        """

        Args:
           parent: this instance's parent object
           text: the text of the text node. This can be changed later
           with self.set_text() .
        """
        text = text or ""
        self._el = document.createTextNode(text)
        if parent is not None:
            parent.appendChild(self)

    def set_text(self, newtext: str) -> None:
        """Change the text of the textnode.

        Args:
           newtext: The new text to set.
        """
        self._el.nodeValue = newtext
        # print("newtextset to '{}'".format(newtext))


def create_elementstring(parent: base_element, idstr: str, attrdct: dict,
                         elementclass, text: str) -> "element":
    """Helper function to create a specified HTML element of class 'elementclass'
    with a textnode in it.

    Args:
       parent: the parent instance of the newly created object.
       idstr: the id string of the newly created object
       attrdct: the attribute dict of the newly created object
       elementclass: the class of the newly created instance
       text: the text of the textnode to be added as a child to the newly created object.

    Returns:
       The element created is returned.

    Example:
      This creates an html.h1 element in the provided view with the
      text 'User Dashboard'::

         title_el = html.create_elementstring(view, 'dashtitle', None,
                                              htmlelements.h1, "User Dashboard")
    """
    el = elementclass(parent, idstr, attrdct)
    textnode(el, text)
    return el


class generic_element(base_element):
    def __init__(self,
                 tagname: str,
                 parent: base_element,
                 idstr: typing.Optional[str],
                 attrdct: typing.Optional[dict],
                 jsel) -> None:
        """Add an HTML element of type tagname to the parent. The new element
        will have an idstr and certain additional attributes as defined in attrdct.

        Args:
           tagname: the kind of html tag to create (e.g. 'p', or 'h1')
           parent: the newly created element is placed under the parent, a python object.\
              If this is None, the element is created in the\
              document.body (i.e. globally in the document)
           idstr: a string identifying the object. If this is None, no id attribute is set.\
              This string, if provided, should be unique within the scope of the complete\
              document in order to be uniquely found.
           attrdct: a dictionary of HTML attributes to set. The exact attributes\
              allowed will depend on the element type.
           jsel: The HTML dom object to wrap around. If this is not provided,\
              a new object is created in the document.\
              If jsel *IS* provided, then the place of the existing element in\
              the DOM hierarchy *is NOT* modified and no addObserver calls are issued.\
              In other words, the parent argument is ignored.

        Note:
           This class recognises special keys of attrdct which are treated separately from
           normal html attributes.
           The names of these attributes start with a star '*', for example, *buttonpressmsg.
           These predefined reserved attributes are used internally to this class.
        """
        do_create = jsel is None
        if do_create:
            jsel = document.createElement(tagname)
        idstr = idstr or ""
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
        """Set attribute names k to value v.

        Args:
           k: name of attribute to set.
           v: value to set the attribute to.
              This should a string for an HTML attribute, but can be anything\
              for a reserved attribute.
        """
        if k.startswith('*'):
            self._locattrdct[k] = v
        else:
            self._el.setAttribute(k, v)

    def getAttribute(self, k: str) -> typing.Optional[typing.Any]:
        """Get the value of an attribute k.

        Args:
           k: the name of the attribute

        Returns:
           None if the attribute does not exist.\
           A string in the case of an HTML attribute.\
           Any data type in the case of a reserved attribute.
        """
        if k.startswith('*'):
            return self._locattrdct.get(k, None)
        else:
            return self._el.getAttribute(k)

    def removeAttribute(self, k: str) -> None:
        """Remove attribute k.

        Args:
           k: the name of the attribute to remove.
        """
        if k.startswith('*'):
            if k in self._locattrdct:
                del self._locattrdct[k]
        else:
            self._el.removeAttribute(k)

    def hasAttribute(self, k: str) -> bool:
        """Determine whether this attribute is set or not.

        Args:
           k: the name of the attribute to check.
        """
        if k.startswith('*'):
            return self._locattrdct.get(k, None) is not None
        else:
            return self._el.hasAttribute(k)

    def rcvMsg(self, whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: typing.Optional[base.MSGdata_Type]):
        """
        Note:
           Unless overridden, every object simply passes on a message to its parent.
        """
        print("element.RECV({}): msg {} from {}: passing to parent..".format(self._idstr, msgdesc, whofrom._idstr))
        if self._parent is not None:
            self._parent.rcvMsg(whofrom, msgdesc, msgdat)

    # parent manipulation -- these are best used in a context manager (ParentUncouple, see below)
    def _removeJSfromParent(self) -> int:
        """Remove this python object's js item from its parent, returning its child index
        before removal. This will allow returning to the same place afterwards.

        Returns:
           The index of the child element removed from the parent.
"""
        jsel = self._el
        jsparent = jsel.parentNode
        child_col = jsparent.children
        ifnd = 0
        while ifnd < child_col.length and child_col[ifnd] != jsel:
            ifnd += 1
        jsparent.removeChild(jsel)
        return ifnd

    def _addJStoParent(self, pos: int) -> None:
        """Add this object's js object into the parent at position pos"""
        if self._parent is not None:
            jsparent = self._parent._el
            child_arr = jsparent.children
            # NOTE: if we set bef_node to null, we add our new element to the end of the list..
            bef_node = child_arr[pos] if pos < child_arr.length else None
            jsparent.insertBefore(self._el, bef_node)


class OnChangeMixin:
    """This is a mixin class that will attach a _changefunc method to the javascript
    onchange event.
    This Mixin only works with objects that have an _addEventListener() method.
    This event is triggered whenever certain HTML elements have been modified by the user,
    see https://developer.mozilla.org/en-US/docs/Web/Events/change

    HTML elements that produce these events include <input>, <select> and <textarea> HTML elements.
    Note: this functionality is provided as a mixin class, because not all HTML elements
    produce the change event.
    """
    def __init__(self) -> None:
        self._addEventListener("change", self._changefunc, False)

    def _changefunc(self):
        msgdat = self._locattrdct.get(base_element.STARATTR_ONCHANGE, None)
        if msgdat is not None:
            print("element._changefunc: '{}' creating onchange event".format(self._idstr))
            self.sndMsg(base.MSGD_ON_CHANGE, msgdat)
        else:
            print("element._changefunc: '{}': got None, ignoring event".format(self._idstr))


class ParentUncouple:
    """A context manager for uncoupling the JS element from a parent during update.
    Uncouple the js element from its parent while we update its
    appearance for speed.
    Recouple the js element at the same location in the parent's list of children on exit."""
    def __init__(self, el: generic_element) -> None:
        self.obj = el
        self.pos: typing.Optional[int] = None

    def __enter__(self):
        self.pos = self.obj._removeJSfromParent()

    def __exit__(self, *args):
        self.obj._addJStoParent(self.pos)


class element(generic_element):
    """A virtual basic html element class. This class exists solely so that all actual
    html elements such as buttons etc., have one common base type.
    The __init__ method of any derived classes must call generic_element.__init__()
    instead of simply super()...
    """
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        """
        Args:
           parent: the parent instance of the object
           idstr: the id string of the object
           attrdct: the attribute dict of the object to create.
           jsel: the optional javascript object to wrap.
        """
        pass


class button(element):
    """An HTML button element.

    Note:
       See https://www.w3schools.com/tags/tag_button.asp
    """
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'button', parent, idstr, attrdct, jsel)


class textbutton(button):
    """A predefined button with text content"""
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, buttontext: str) -> None:
        button.__init__(self, parent, idstr, attrdct, None)
        self._textnode = textnode(self, buttontext)


class h1(element):
    """An HTML h1 (header level 1) element

    Note:
     See https://www.w3schools.com/html/html_headings.asp
    """
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'h1', parent, idstr, attrdct, jsel)


class h2(element):
    """An HTML h2 (header level 2) element

    Note:
     See https://www.w3schools.com/html/html_headings.asp
    """
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'h2', parent, idstr, attrdct, jsel)


# NOTE: 2018-07-30 For some reason, cannot use super() in h1text or h2 text, as this
# leads to infinite recursion in javascript...
class h1text(h1):
    """A predefined h1 text element."""
    def __init__(self, parent: base_element, h1text: str) -> None:
        idstr = ""
        h1.__init__(self, parent, idstr, {}, None)
        self._textnode = textnode(self, h1text)


class h2text(h2):
    """A predefined h2 text element."""
    def __init__(self, parent: base_element, h2text: str) -> None:
        idstr = ""
        h2.__init__(self, parent, idstr, {}, None)
        self._textnode = textnode(self, h2text)


class h3(element):
    """An HTML h3 (header level 3) element
    Note:
     See https://www.w3schools.com/html/html_headings.asp
    """
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'h3', parent, idstr, attrdct, jsel)


class p(element):
    """A paragraph element.

    Note:
     See https://www.w3schools.com/html/html_paragraphs.asp
    """
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'p', parent, idstr, attrdct, jsel)


class div(element):
    """A HTML div element.

    Note:
       See https://www.w3schools.com/html/html_blocks.asp
    """

    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'div', parent, idstr, attrdct, jsel)


class span(element):
    """A span element.

    Note:
       See https://www.w3schools.com/html/html_blocks.asp
    """
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'span', parent, idstr, attrdct, jsel)


class header(element):
    """A header element.

    Note:
       See https://www.w3schools.com/html/html_blocks.asp
    """
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'header', parent, idstr, attrdct, jsel)


class footer(element):
    """A footer element.

    Note:
       See https://www.w3schools.com/html/html_blocks.asp
    """
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

    Note:
       Set the href attribute in attrdct for the link destination.

    Note: https://www.w3schools.com/html/html_links.asp
    """
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'a', parent, idstr, attrdct, jsel)


class img(element):
    """An image element.

    Note:
       See https://www.w3schools.com/html/html_images.asp

    Note:
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
    """A table row element

    Note:
       See https://www.w3schools.com/html/html_tables.asp
    """

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
    """A table header element.

    Note:
     See https://www.w3schools.com/html/html_tables.asp
    """

    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'th', parent, idstr, attrdct, jsel)


class td(element):
    """A table data cell element.

    Note:
       See https://www.w3schools.com/html/html_tables.asp
    """

    def __init__(self, parent: base_element, idstr: str, attrdct: typing.Optional[dict], jsel) -> None:
        generic_element.__init__(self, 'td', parent, idstr, attrdct, jsel)


# orders and unordered lists, and list items
class ol(element):
    """An ordered list of li items.

    Note:
       See https://www.w3schools.com/html/html_lists.asp
    """
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'ol', parent, idstr, attrdct, jsel)


class ul(element):
    """An unordered list (bullet list) of list items.

    Note:
     See See https://www.w3schools.com/html/html_lists.asp
"""

    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'ul', parent, idstr, attrdct, jsel)


class li(element):
    """A list item element"""

    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'li', parent, idstr, attrdct, jsel)


class label(element):
    """A label element.
    A label tag defines a label (i.e. some text that accompanies another element) for
    another element such as a button, input or output element etc.

    Note:
       See https://www.w3schools.com/tags/tag_label.asp
    """
    def __init__(self,
                 parent: base_element,
                 idstr: str,
                 attrdct: dict,
                 labeltext: str,
                 jsel) -> None:
        generic_element.__init__(self, 'label', parent, idstr, attrdct, jsel)
        self.set_text(labeltext)

    def set_text(self, labeltext: str) -> None:
        self.setInnerHTML(labeltext)
        self._mytext = labeltext

    def get_text(self) -> str:
        return self._mytext


class option(element):
    """An option element that goes inside a select element.

    Note:
       See https://www.w3schools.com/html/html_form_elements.asp
    """

    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'option', parent, idstr, attrdct, jsel)


class select(element, OnChangeMixin):
    """A select element. We also keep a list of options (python objects).

    Note:
       See https://www.w3schools.com/html/html_form_elements.asp
"""
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        generic_element.__init__(self, 'select', parent, idstr, attrdct, jsel)
        OnChangeMixin.__init__(self)
        self._optlst: typing.List[option] = []
        self._optdct: typing.Dict[str, option] = {}

    def get_selected(self) -> typing.Tuple[typing.Optional[int], typing.Optional[str]]:
        """
        Returns:
           the currently selected index and value string.\
           It may be that no element is selected. In this case, selectedIndex will
        return a value of -1. Return None, None in this case.
        """
        sel_ndx = self._el.selectedIndex
        if sel_ndx == -1:
            return (None, None)
        val = self._el.options[sel_ndx].value
        return (int(sel_ndx), val)

    def set_selected(self, idstr: str) -> None:
        """Make the option with the provided idstr the currently selected
        option.
        This is achieved by setting the selected attribute of the designated
        option item.
        If no idstr is found, a message is written to console and the function
        returns.
        """
        opt = self._optdct.get(idstr, None)
        if opt is None:
            print("select: no option with idstr: {}".format(idstr))
            return
        for iidstr, opt in self._optdct.items():
            if iidstr == idstr:
                opt.setAttribute('selected')
            else:
                opt.removeAttribute('selected')

    def has_option_id(self, idstr: str) -> bool:
        """Return 'the select element has an option field with an id == idstr' """
        return self._optdct.get(idstr, None) is not None

    def num_options(self) -> int:
        """Return the number of options"""
        return len(self._optlst)

    def _add_option(self, idstr: str, name: str) -> None:
        """Add an option to the end of the option list.
        The HTML value of the option becomes idstr and the displayed string is 'name'.
        """
        optattrdct = {'value': idstr}
        opt = option(self, "locopt{}".format(idstr), optattrdct, None)
        opt.setInnerHTML(name)
        self._optlst.append(opt)
        self._optdct[idstr] = opt

    def add_or_set_option(self, idstr: str, name: str) -> None:
        """Add a new option to the select .
        Each option has a unique  idstr for identification of the option
        and a name which is displayed.
        """
        opt = self._optdct.get(idstr, None)
        if opt is None:
            self._add_option(idstr, name)
        else:
            opt.setInnerHTML(name)


class input(element, OnChangeMixin):
    """An input HTML element.
    Input elements are primarily used in HTML forms as the various ways of allowing
    the user to enter data (such as text, toggle buttons, submit buttons)
    into the HTML form.
    """
    def __init__(self, parent: base_element, idstr: str,
                 inp_type: str, attrdct: dict, jsel) -> None:
        """
        Args:
           parent: the python parent instance
           idstr: the id string
           inp_type: one of the HTML-defined input types e.g. 'button', 'checkbox' etc.\
              see https://www.w3schools.com/tags/tag_input.asp
           attrdct: a dict of HTML attributes.
        """
        if attrdct is None:
            attrdct = {'type': inp_type}
        else:
            attrdct['type'] = inp_type
        generic_element.__init__(self, 'input', parent, idstr, attrdct, jsel)
        OnChangeMixin.__init__(self)

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


class input_checkbox(input):
    """An HTML input checkbox class
    """
    def __init__(self, parent: base_element, idstr: str, attrdct: dict, jsel) -> None:
        super().__init__(parent, idstr, 'checkbox', attrdct, jsel)
        self.set_checked(False)

    def set_checked(self, on: bool) -> None:
        """Set the checked state to on/off"""
        self._el.checked = on

    def get_checked(self) -> bool:
        """Return the checked state of the checkbox."""
        return self._el.checked


class LEDElement(div):
    """A coloured round LED indicator button.

    Note:
       The colours of this element are created by CSS style sheets (assets/css/leds.css).
    """
    RED = 0
    YELLOW = 1
    GREEN = 2
    BLUE = 3

    def __init__(self, parent: base_element,
                 idstr: str,
                 attrdct: dict,
                 jsel,
                 initial_colour: int = 0) -> None:
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


def scoalert(txt: str) -> None:
    """Opens a blocking dialog with an 'OK' button The txt is presented.

    Args:
       txt: the text to display to the user.
    """
    alert(txt)


class alertbox(div):
    """A box that displays text to catch a user's attention."""
    def __init__(self, parent: base_element,
                 idstr: str,
                 attrdct: dict,
                 jsel) -> None:
        attrdct = attrdct or {}
        attrdct['class'] = 'alert'
        super().__init__(parent, idstr, attrdct, jsel)
        self.txt = textnode(self, "")

    def set_text(self, newtext: str) -> None:
        self.txt.set_text(newtext)
