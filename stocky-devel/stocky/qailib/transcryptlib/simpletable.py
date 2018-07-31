# Utility module for creating simple tables


import typing
# import qailib.common.base as base

import qailib.transcryptlib.htmlelements as html


class simpletable(html.element):
    """ A really simple table class.
    The dimensions of the table are given at instantiation, further rows can be added later.
    Columns cannot be added.
    """
    def __init__(self,
                 parent: html.base_element,
                 idstr: str, attrdct: dict,
                 numrows: int, numcols: int) -> None:
        html.generic_element.__init__(self, 'table', parent, idstr, attrdct, None)
        self.numcols = numcols
        self._rowlst: typing.List[html.tr] = []
        self.td_dct: typing.Dict[typing.Tuple[int, int], html.td] = {}
        for nr in range(numrows):
            self.append_row()

    def numrows(self) -> int:
        """Return the number of rows in the table"""
        return len(self._rowlst)

    def append_row(self) -> int:
        """Add a new row to the table, and return the new row's number."""
        idstr = self._idstr
        nr = self.numrows()
        td_dct = self.td_dct
        rowattrdct: typing.Dict = {}
        cellattrdct = rowattrdct
        newrow = html.tr(self, "{}-r{}".format(idstr, nr), rowattrdct, None)
        self._rowlst.append(newrow)
        for nc in range(self.numcols):
            td_dct[(nr, nc)] = html.td(newrow, "{}-c{}x{}".format(idstr, nr, nc), cellattrdct, None)
        return nr

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

    def delete_rows(self) -> None:
        """Delete all rows in the table."""
        NN = self.numrows()
        for ndx in range(NN):
            # this is a javascript call...
            self._el.deleteRow(0)
        # for ndx, r in enumerate(self._rowlst):
        #    del r
        self._rowlst = []


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
        self._tabdct: typing.Dict[str, html.spantext] = {}
        tabdct = self._tabdct
        kattrdct = {'class': "w3-tag w3-red"}
        vattrdct = {'class': "w3-tag"}
        for rownum, tup in enumerate(tup_lst):
            k, v = tup
            kcell = self.getcell(rownum, 0)
            if kcell is not None:
                html.label(kcell, "", kattrdct, k, None)
            else:
                print("ERROR in dict_table 0")
            #
            vcell = self.getcell(rownum, 1)
            if vcell is not None:
                vtext = "{}".format(v)
                tabdct[k] = html.spantext(vcell, "", vattrdct, vtext)
                self.set_alignment(rownum, 1, 'right')
            else:
                print("ERROR in dict_table 1")

    def update_table(self, new_dct: dict) -> None:
        """Update the tables values from new_dct"""
        tabdct = self._tabdct
        for k, v in new_dct.items():
            tabdct[k].set_text("{}".format(v))
