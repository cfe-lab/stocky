

# Provide a thin wrapper around the SVG.js library
import typing
from org.transcrypt.stubs.browser import SVG

import qailib.transcryptlib.htmlelements as html

SVGShape = typing.Any


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
        self.curels = []
        # print("YAHOOO {} {}".format(w, h))
        # self.myrect = self.drawing.rect(w-10, h-10).attr({'fill': '#f06'})

    def clear(self) -> None:
        for dd in self.curels:
            dd.remove()
        self.curels = []

    def rect(self, x: int, y: int, w: int, h: int, colorstr: str) -> SVGShape:
        dd = self.drawing.rect(w, h).move(x, y).attr({'fill': colorstr})
        self.curels.append(dd)
        return dd

    def text(self, x: int, y: int, colorstr: str, text_str: str) -> SVGShape:
        dd = self.drawing.text(text_str).move(x, y).attr({'fill': colorstr})
        self.curels.append(dd)
        return dd
