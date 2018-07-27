# Utility module for creating simple tables


import typing
# import qailib.common.base as base

import qailib.transcryptlib.htmlelements as html


class simpletable(html.element):
    def __init__(self,
                 parent: html.base_element,
                 idstr: str, attrdct: dict,
                 numrows: int, numcols: int) -> None:
        html.generic_element.__init__(self, 'table', parent, idstr, attrdct, None)
        self.numrows = numrows
        self.numcols = numcols
        self.td_dct = td_dct = {}
        cellattrdct = rowattrdct = {}
        for nr in range(numrows):
            newrow = html.tr(self, "{}-r{}".format(idstr, nr), rowattrdct, None)
            for nc in range(numcols):
                td_dct[(nr, nc)] = html.td(newrow, "{}-c{}x{}".format(idstr, nr, nc), cellattrdct, None)

    def getcell(self, rownum: int, colnum: int) -> typing.Optional[html.td]:
        return self.td_dct.get((rownum, colnum), None)

    def set_alignment(self, rownum: int, colnum: int, alignstr: str) -> None:
        """Set the alignment of the given cell by setting the style attribute
        style = "text-align:alignstr , where
        alignstr is one of left, right, center
        """
        cell = self.td_dct.get((rownum, colnum), None)
        if cell is not None:
            cell.setAttribute('style', "text-align:{}".format(alignstr))
