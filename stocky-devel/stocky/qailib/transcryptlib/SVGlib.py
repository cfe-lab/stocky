

# Provide a thin wrapper around the SVG.js library
import typing
from org.transcrypt.stubs.browser import SVG

import qailib.transcryptlib.htmlelements as html


class svg(html.element):
    def __init__(self, parent: html.base_element,
                 idstr: str,
                 attrdct: dict,
                 jsel,
                 sizetup: typing.Tuple[str, str]) -> None:
        html.generic_element.__init__(self, 'div', parent, idstr, attrdct, jsel)
        self.drawing = SVG(idstr)
        if sizetup is None:
            w = h = '100%'
        else:
            w, h = sizetup
        self.drawing.size(w, h)
        w, h = self.get_WH()
        print("YAHOOO {} {}".format(w, h))
        self.rect = self.drawing.rect(w-10, h-10).attr({'fill': '#f06'})

