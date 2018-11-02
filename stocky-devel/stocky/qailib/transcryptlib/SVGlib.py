"""Provide a thin wrapper around the SVG.js library
   https://svgjs.com/

   For this module to work in the browser at run-time, SVG.js must be loaded
   into the browser in the HTML pages.
"""

import typing
try:
    from org.transcrypt.stubs.browser import SVG
except ModuleNotFoundError:
    pass
import qailib.transcryptlib.htmlelements as html

SVGShape = typing.Any


class svg(html.element):
    """An SVG canvas rectangle"""
    def __init__(self, parent: html.base_element,
                 idstr: str,
                 attrdct: typing.Optional[dict],
                 jsel,
                 sizetup: typing.Optional[typing.Tuple[str, str]]) -> None:
        """

        Args:
           parent: the parent of the SVG element
           idstr: the id string
           attrdct: the aHTML attribute dict
           jsel: an optional existing javascript element to use.
           sizetup: an optional tuple of strings describing the size of the SVG\
               canvas in the usual HTML dimensions (pizels, percentages etc.).
               If none is provided, ('100%', '100%') is used.
        """
        html.generic_element.__init__(self, 'div', parent, idstr, attrdct, jsel)
        self.curels: typing.List[SVGShape] = []
        self.drawing = SVG(idstr)
        if sizetup is None:
            ws = hs = '100%'
        else:
            ws, hs = sizetup
        self.drawing.size(ws, hs)
        # w, h = self.get_WH()
        # print("YAHOOO {} {}".format(w, h))
        # self.myrect = self.drawing.rect(w-10, h-10).attr({'fill': '#f06'})

    def clear(self) -> None:
        """Remove all elements on the canvas."""
        for dd in self.curels:
            dd.remove()
        self.curels = []

    def rect(self, x: int, y: int, w: int, h: int, colorstr: str) -> SVGShape:
        """Draw a rectangle.

        Args:
           x: x-coordinate of the top left corner
           y: y-coordinate of the top left corner
           w: width of rectangle
           h: height of rectangle
           colorstr: a string describing the colour of the rectangle.\
              This is a hex RGB value, e.g. '#ff0066' for a reddish colour.
        Returns:
           The svg item created.
        """
        dd = self.drawing.rect(w, h).move(x, y).attr({'fill': colorstr})
        self.curels.append(dd)
        return dd

    def text(self, x: int, y: int, colorstr: str, text_str: str) -> SVGShape:
        """Draw some text.

        Args:
           x: x-coordinate of the top left corner
           y: y-coordinate of the top left corner
           colorstr: a string describing the colour of the rectangle.\
              This is a hex RGB value, e.g. '#ff0066' for a reddish colour.
           text_str: the text to display
        """
        dd = self.drawing.text(text_str).move(x, y).attr({'fill': colorstr})
        self.curels.append(dd)
        return dd
