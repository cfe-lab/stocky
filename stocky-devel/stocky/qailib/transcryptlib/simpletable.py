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


class dict_table(simpletable):
    """Display the contents of a dict (key: val) per row. as text.
    The order of the rows is provided by the initial tuple list.
    """
    def __init__(self,
                 parent: html.base_element,
                 idstr: str,
                 attrdct: dict,
                 tup_lst) -> None:
        numrows = len(tup_lst)
        super().__init__(parent, idstr, attrdct, numrows, 2)
        self._tabdct = tabdct = {}
        kattrdct = {'class': "w3-tag w3-red"}
        vattrdct = {'class': "w3-tag"}
        for rownum, tup in enumerate(tup_lst):
            k, v = tup
            kcell = self.getcell(rownum, 0)
            html.label(kcell, "", kattrdct, k, None)
            #
            vcell = self.getcell(rownum, 1)
            vtext = "{}".format(v)
            
            tabdct[k] = html.spantext(vcell, "", vattrdct, vtext)
            self.set_alignment(rownum, 1, 'right')

    def update_table(self, new_dct: dict) -> None:
        """Update the tables values from new_dct"""
        tabdct = self._tabdct
        for k, v in new_dct.items():
            tabdct[k].set_text("{}".format(v))
