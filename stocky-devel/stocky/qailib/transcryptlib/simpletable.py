""" A utility module for creating simple HTML tables.
All of these classes are based on classes from htmlelements
for tables, but add some methods for ease of use.
"""


import typing
import qailib.transcryptlib.htmlelements as html

TOP_OF_TABLE = 0
END_OF_TABLE = -1


class datacell(html.td):
    """Every element in a simpletable is a datacell.
    This is a subclass of htmlelements.td
    """
    def __init__(self,
                 parent: html.base_element,
                 idstr: str,
                 attrdct: typing.Optional[dict]) -> None:
        """
        Args:
           parent: the parent object (typically the table)
           idstr: the id of the data cell
           attrdct: the attribute dict for the HTML element.
        """
        html.td.__init__(self, parent, idstr, attrdct, None)
        self._cont: typing.Optional[html.base_element] = None

    def set_content(self, newcont: typing.Optional[html.base_element]) -> None:
        self._cont = newcont

    def get_content(self) -> typing.Optional[html.base_element]:
        return self._cont


class baserow(html.tr):
    """Every row in a simpletable is a subclass of baserow.
    This is a subclass of htmlelements.tr
    """
    def __init__(self, parent: html.base_element,
                 idstr: str,
                 attrdct: typing.Optional[dict],
                 jsel) -> None:
        """
        Args:
           parent: the parent object
           idstr: the id of the data row
           attrdct: the attribute dictionary for the HTML element.
           jsel: an optional underlying javascript object
        """
        html.tr.__init__(self, parent, idstr, attrdct, jsel)
        self.isnew = True


class datarow(baserow):
    """A table row that contains data elements."""
    def __init__(self, parent: html.base_element,
                 idstr: str,
                 attrdct: typing.Optional[dict],
                 jsel,
                 numcols: int) -> None:
        """
        Args:
           parent: the parent object
           idstr: the id of the data row
           attrdct: the attribute dictionary for the HTML element.
           jsel: an optional underlying javascript object
           numcols: the number of columns in the data row.
        """
        baserow.__init__(self, parent, idstr, attrdct, jsel)
        self._cellst: typing.List[datacell] = []
        cellattrdct: typing.Dict = {}
        fmtstr = idstr + "-c{}"
        for nc in range(numcols):
            self._cellst.append(datacell(self,
                                         fmtstr.format(nc),
                                         cellattrdct))

    def getcell(self, colnum: int) -> typing.Optional[datacell]:
        """Access a data cell by cell number in the row.

        Args:
           colnum: the column number of the data cell to return.

        Returns:
           The data cell or None if colnum is out of range.
        """
        lst = self._cellst
        return lst[colnum] if 0 <= colnum < len(lst) else None

    def getcellcontent(self, colnum: int) -> typing.Optional[html.base_element]:
        """Access a data cell content by cell number in the row.

        Args:
           colnum: the column number of the data cell to return.

        Returns:
           The data cell content or None if colnum is out of range.
        """
        retcell = self.getcell(colnum)
        return retcell.get_content() if retcell is not None else None

    def setcellcontent(self, colnum: int,
                       newcont: typing.Optional[html.base_element]) -> None:
        """Set data cell content by cell number.

        Args:
           colnum: the column number of the data cell to return.
           newcont: the new content to set.
        """
        cell = self.getcell(colnum)
        if cell is not None:
            cell.set_content(newcont)


class headerrow(baserow):
    """A table row that contains header elements."""
    def __init__(self, parent: html.base_element,
                 idstr: str,
                 attrdct: typing.Optional[dict],
                 jsel,
                 numcols: int) -> None:
        """
        Args:
           parent: the parent object
           idstr: the id of the data row
           attrdct: the attribute dictionary for the HTML element.
           jsel: an optional underlying javascript object
           numcols: the number of columns in the data row.
        """
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
    """A really simple table class.
    The dimensions of the table (number of rows and columns) are given at instantiation.
    Rows can be added or removed later (see :py:meth:`append_row`
    and :py:meth:`adjust_row_number`).
    The row numbering starts from 0, which visibly represents the top row on the web page.

    The number columns in each row cannot be changed after instantiation.
    Column numbering also starts at 0, which visibly is the left of the page.

    A header row, which can be used to display column headers for the table,
    may be optionally added (see :py:meth:`add_header_row`). The presence or absence
    of a header row does not effect the numbering of the data rows.

    Alignment of content within each data cell of the table may be set by calling
    :py:meth:`set_alignment` .
    """
    def __init__(self,
                 parent: html.base_element,
                 idstr: str,
                 attrdct: dict,
                 numrows: int,
                 numcols: int) -> None:
        """

        Args:
           parent: the HTML parent of this table
           idstr: the table's id string.
           attrdct: an HTML attribute dict.
           numrows: the number of table rows. These are data rows, excluding any header row.
           numcols: the number of columns on each row in the table.
        """
        html.generic_element.__init__(self, 'table', parent, idstr, attrdct, None)
        self.numcols = numcols
        self._rowlst: typing.List[datarow] = []
        self._rowcache: typing.List[datarow] = []
        for nr in range(numrows):
            self.append_row()
        self._headerrow: typing.Optional[headerrow] = None

    def numrows(self) -> int:
        """Return the number of data rows in the table.
        This does not include the optional header row.

        Returns:
           Return the number of rows in the table,
        """
        return len(self._rowlst)

    def getrow(self, rownum: int) -> typing.Optional[datarow]:
        """Return the data row instance by its number.
        Args:
           rownum: the row number to return [0.. self.numrows()-1]

        Returns:
           The determined data row or None if rownum is out of range.
        """
        rowlst = self._rowlst
        # print("getrow {}  {}".format(rownum, len(rowlst)))
        return rowlst[rownum] if 0 <= rownum < len(rowlst) else None

    def has_header_row(self) -> bool:
        """
        Returns:
           True if a header row has been added to the table.
        """
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
        """Add a header row to the table.
        The header row does not have any contents.
        """
        if self._headerrow is None:
            idstr = self._idstr
            rowattrdct: typing.Dict = {}
            jsrow = self._el.insertRow(TOP_OF_TABLE)
            self._headerrow = headerrow(self,
                                        "{}-HDR".format(idstr),
                                        rowattrdct,
                                        jsrow, self.numcols)

    def getheader(self, colnum: int) -> typing.Optional[html.th]:
        """Get a cell from the header row,
        Args:
           colnum: the column number to retrieve.
        Returns:
           The th instance at position colnum. If there is no header, or
           colnum is out of range, None is returned.
        """
        hr = self._headerrow
        return hr.getcell(colnum) if hr is not None else None

    def append_row(self) -> int:
        """Add a new empty row to the end of the table, and return the new row's number.

        Returns:
           the number of the newly added row.
        """
        idstr = self._idstr
        nr = self.numrows()
        rowattrdct: typing.Dict = {}
        newrow = self._insertRow(END_OF_TABLE, "{}-r{}".format(idstr, nr), rowattrdct)
        self._rowlst.append(newrow)
        return nr

    def getcell(self, rownum: int, colnum: int) -> typing.Optional[datacell]:
        """Return a table cell at location (rownum, colnum).

        Args:
           rownum: row number
           colnum: the column number
        Returns:
           The datacell determined, or None if rownum or colnum are out of range.
        See also:
           :py:meth:`getcellcontent` :py:meth:`setcellcontent`
        """
        row = self.getrow(rownum)
        return row.getcell(colnum) if row is not None else None

    def getcellcontent(self, rownum: int, colnum: int) -> typing.Optional[html.base_element]:
        """Return cell content at a location (rownum, colnum).

        Args:
           rownum: row number
           colnum: the column number
        Returns:
           The datacell content determined, or None if rownum or colnum are out of range.
        See also:
           :py:meth:`getcell`
        """
        retcell = self.getcell(rownum, colnum)
        return retcell.get_content() if retcell is not None else None

    def setcellcontent(self, rownum: int, colnum: int,
                       newcont: typing.Optional[html.base_element]) -> None:
        """Replace the cell content with new content.

        Args:
           rownum: the row number
           colnum: the column number
           newcont: the new content to place in the data cell.

        Note:
           If rownum or colnum are out of range, this routine silently fails.
        See also:
           :py:meth:`getcellcontent` :py:meth:`getcell`
        """
        retcell = self.getcell(rownum, colnum)
        if retcell is not None:
            retcell.set_content(newcont)

    def set_alignment(self, rownum: int, colnum: int, alignstr: str) -> None:
        """Set the alignment of the given cell by setting the style attribute.

        Args:
           rownum: the row number
           colnum: the column number
           alignstr: one of one of 'left', 'right' or 'center'
        Note:
           This works by setting the HTML style attribute to something of the form:
           style = "text-align:alignstr", where alignstr is the value of the argument above.
           This routine silently fails if rownum or colnum are out of range.
        """
        cell = self.getcell(rownum, colnum)
        if cell is not None:
            cell.setAttribute('style', "text-align:{}".format(alignstr))

    def adjust_row_number(self, newn: int) -> None:
        """Increase or decrease the number of visible rows in the table,
        not including the header row.

        Args:
           newn: the desired number of data rows in the table.

        Note: Rows are always added to or removed from the **end of the table**.
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
    """Display the contents of a dict in table form. The table will have two
    columns, with the key in column zero and its corresponsing value in column 1
    on the same row.
    The order of the rows is provided by the initial tuple list.

    The entries in the values column (column 1) can be updated at a later stage by
    calling :py:meth:`update_table`
    """
    def __init__(self,
                 parent: html.base_element,
                 idstr: str,
                 attrdct: dict,
                 tup_lst) -> None:
        """
        Args:
           parent: the HTML parent of this table
           idstr: the table's id string.
           attrdct: an HTML attribute dict.
           tup_lst: a list of (key, value) tuples used to fill the table with values.
        """
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
        """Update the tables values from new_dct.

        Args:
           new_dct: a dict from which to update the values column (column 1)\
              in the table. new_dct may not have keys absent in the original tup_lst.
        """
        tabdct = self._tabdct
        self.set_visible(False)
        for k, v in new_dct.items():
            tabdct[k].set_text("{}".format(v))
        self.set_visible(True)
