# Utility module for creating simple tables


import typing
# from org.transcrypt.stubs.browser import document
# import qailib.common.base as base

import qailib.transcryptlib.htmlelements as html

TOP_OF_TABLE = 0
END_OF_TABLE = -1

class datacell(html.td):
    def __init__(self,
                 parent: html.base_element,
                 idstr: str,
                 attrdct: typing.Optional[dict]) -> None:
        html.td.__init__(self, parent, idstr, attrdct, None)
        self._cont: typing.Optional[html.base_element] = None

    def set_content(self, newcont: typing.Optional[html.base_element]) -> None:
        self._cont = newcont

    def get_content(self) -> typing.Optional[html.base_element]:
        return self._cont

class baserow(html.tr):
    def __init__(self, parent: html.base_element,
                 idstr: str,
                 attrdct: typing.Optional[dict],
                 jsel) -> None:
        html.tr.__init__(self, parent, idstr, attrdct, jsel)
        self.isnew = True

class datarow(baserow):
    def __init__(self, parent: html.base_element,
                 idstr: str,
                 attrdct: typing.Optional[dict],
                 jsel,
                 numcols: int) -> None:
        baserow.__init__(self, parent, idstr, attrdct, jsel)
        self._cellst: typing.List[datacell] = []
        cellattrdct: typing.Dict = {}
        fmtstr = idstr + "-c{}"
        for nc in range(numcols):
            self._cellst.append(datacell(self,
                                         fmtstr.format(nc),
                                         cellattrdct))

    def getcell(self, colnum: int) -> typing.Optional[datacell]:
        lst = self._cellst
        return lst[colnum] if 0 <= colnum < len(lst) else None

    def getcellcontent(self, colnum: int) -> typing.Optional[html.base_element]:
        retcell = self.getcell(colnum)
        return retcell.get_content() if retcell is not None else None

    def setcellcontent(self, colnum: int,
                       newcont: typing.Optional[html.base_element]) -> None:
        cell = self.getcell(colnum)
        if cell is not None:
            cell.set_content(newcont)


class headerrow(baserow):
    def __init__(self, parent: html.base_element,
                 idstr: str,
                 attrdct: typing.Optional[dict],
                 jsel,
                 numcols: int) -> None:
        baserow.__init__(self, parent, idstr, attrdct, jsel)
        cellattrdct: typing.Dict = {}
        self._cellst: typing.List[html.th] = []
        for nc in range(numcols):
            self._cellst.append(html.th(self, "{}-H{}".format(idstr, nc),
                                        cellattrdct, None))

    def getcell(self, colnum: int) -> typing.Optional[html.th]:
        lst = self._cellst
        return lst[colnum] if 0 <= colnum < len(lst) else None


class simpletable(html.element):
    """ A really simple table class.
    The dimensions of the table are given at instantiation, further rows can be added later.
    Columns cannot be added.
    The row numbering starts from 0 (the top row).
    """
    def __init__(self,
                 parent: html.base_element,
                 idstr: str, attrdct: dict,
                 numrows: int, numcols: int) -> None:
        html.generic_element.__init__(self, 'table', parent, idstr, attrdct, None)
        self.numcols = numcols
        self._rowlst: typing.List[datarow] = []
        self._rowcache: typing.List[datarow] = []
        for nr in range(numrows):
            self.append_row()
        self._headerrow: typing.Optional[headerrow] = None

    def numrows(self) -> int:
        """Return the number of rows in the table, not including the optional header row"""
        return len(self._rowlst)

    def getrow(self, rownum: int) -> typing.Optional[datarow]:
        """Return the data row [0.. self.numrows()-1] or None """
        rowlst = self._rowlst
        # print("getrow {}  {}".format(rownum, len(rowlst)))
        return rowlst[rownum] if 0 <= rownum < len(rowlst) else None

    def has_header_row(self) -> bool:
        return self._headerrow is not None

    def _insertRow(self, rowndx: int, idstr: str, attrdct: typing.Optional[dict]) -> datarow:
        """Insert a row element at the specified position
        and return the created python object...
        rowndx 0 = top of table, -1 end of table.
        """
        no_cache = True
        if no_cache or len(self._rowcache) == 0:
            # make a new one...
            jsrow = self._el.insertRow(rowndx)
            # jsrow = document.createElement('tr')
            # self._el.appendChild(jsrow)
            retval = datarow(self, idstr, attrdct, jsrow, self.numcols)
        else:
            # retrieve one we made earlier...
            retval = self._rowcache.pop()
            retval.isnew = False            
            # insert into the table...
            self._el.insertBefore(retval._el, self._el.childNodes[rowndx])
        return retval

    def add_header_row(self) -> None:
        """Add a header row to the table."""
        if self._headerrow is None:
            idstr = self._idstr
            rowattrdct: typing.Dict = {}
            jsrow = self._el.insertRow(TOP_OF_TABLE)
            self._headerrow = headerrow(self, 
                                        "{}-HDR".format(idstr),
                                        rowattrdct,
                                        jsrow, self.numcols)

    def getheader(self, colnum: int) -> typing.Optional[html.th]:
        hr = self._headerrow
        return hr.getcell(colnum) if hr is not None else None

    def append_row(self) -> int:
        """Add a new row to the table, and return the new row's number."""
        idstr = self._idstr
        nr = self.numrows()
        rowattrdct: typing.Dict = {}
        newrow = self._insertRow(END_OF_TABLE, "{}-r{}".format(idstr, nr), rowattrdct)
        self._rowlst.append(newrow)
        return nr

    def getcell(self, rownum: int, colnum: int) -> typing.Optional[datacell]:
        """Return a table cell at location (rownum, colnum).
        if do_empty_cell, then remove any children in the cell
        before returning it.

        None is returned iff no cell is found."""
        row = self.getrow(rownum)
        return row.getcell(colnum) if row is not None else None

    def setcellcontent(self, rownum: int, colnum: int,
                       newcont: typing.Optional[html.base_element]) -> None:
        retcell = self.getcell(rownum, colnum)
        if retcell is not None:
            retcell.set_content(newcont)

    def getcellcontent(self, rownum: int, colnum: int) -> typing.Optional[html.base_element]:
        retcell = self.getcell(rownum, colnum)
        return retcell.get_content() if retcell is not None else None
    
    def set_alignment(self, rownum: int, colnum: int, alignstr: str) -> None:
        """Set the alignment of the given cell by setting the style attribute
        style = "text-align:alignstr , where
        alignstr is one of left, right, center
        """
        cell = self.getcell(rownum, colnum)
        if cell is not None:
            cell.setAttribute('style', "text-align:{}".format(alignstr))

    def adjust_row_number(self, newn: int) -> None:
        """Increase or decrease the number of visible rows in the table,
        not including the header row.
        """
        ngot = self.numrows()
        if ngot < newn:
            # add rows to table
            print("add rows {}".format(newn-ngot))
            for i in range(newn-ngot):
                self.append_row()
        elif ngot > newn:
            # remove rows from end of table
            print("rem rows {}".format(ngot-newn))
            for i in range(ngot-newn):
                del_row = self._rowlst.pop()
                jsrow = del_row._el
                jsrow.parentNode.removeChild(jsrow)
                # self._el.deleteRow(END_OF_TABLE)
                self._rowcache.append(del_row)
        
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
        self.set_visible(False)
        for k, v in new_dct.items():
            tabdct[k].set_text("{}".format(v))
        self.set_visible(True)
