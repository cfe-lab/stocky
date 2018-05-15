
import typing
import sqlite3

import serverlib.timelib as timelib

# string of length 1
opcodetype = str

locidtype = int
itemidtype = int


class LocChange:
    confirmLocation = 'O'
    markMissing = 'M'
    changeLocation = 'C'

    valid_opcode_lst = [confirmLocation, markMissing, changeLocation]
    valid_opcode_set = frozenset(valid_opcode_lst)

    def __init__(self, itemid: itemidtype, timestamp: timelib.DateTimeType,
                 oldlocid: locidtype, newlocid: locidtype,
                 opcode: opcodetype) -> None:
        self.itemid = itemid
        if not isinstance(timestamp, timelib.DateTimeType):
            raise RuntimeError("timestamp must be a datetime")
        self.ts = timestamp
        self.oldlocid = oldlocid
        self.newlocid = newlocid
        self.opcode = opcode

    def __str__(self) -> str:
        return "{} {} {} {} {}".format(self.itemid, self.ts, self.oldlocid,
                                       self.newlocid, self.opcode)

    def __eq__(self, ot: object) -> bool:
        """We have to implement the == operator so that we can check for
        equivalence in the tests.
        """
        if not isinstance(ot, LocChange):
            return NotImplemented
        return self.itemid == ot.itemid and \
            self.ts == ot.ts and \
            self.oldlocid == ot.oldlocid and \
            self.newlocid == ot.newlocid and \
            self.opcode == ot.opcode

    def has_valid_opcode(self) -> bool:
        return self.opcode in LocChange.valid_opcode_set

    def as_dict(self):
        """Return this instance in dict form.
        NOTE: the timestamp value is returned unmodified.
        """
        return {'itemid': self.itemid,
                'ts': self.ts,
                'oldlocid': self.oldlocid,
                'newlocid': self.newlocid,
                'opcode': self.opcode}

    @staticmethod
    def from_dict(d: dict) -> "LocChange":
        """Create a new LocChange instance from a serialised dictionary"""
        assert isinstance(d, dict), "dict instance expected"
        klst = ['itemid', 'ts', 'oldlocid', 'newlocid', 'opcode']
        val_lst = [d[k] for k in klst]
        # check for the datetime, entry...
        dt = val_lst[1]
        if isinstance(dt, str):
            val_lst[1] = dt = timelib.str_to_datetime(dt)
        tup = tuple(val_lst)
        return LocChange(*tup)


class LocChangeList:

    def __init__(self, fname: str=None) -> None:
        """Initialise an empty location change file.
        if fname is None, then create a db in memory.
        """
        ff = fname or ':memory:'
        self.conn = sqlite3.connect(ff, detect_types=sqlite3.PARSE_DECLTYPES)
        self.initdb()

    def initdb(self):
        """Create tables to store the location changes.
        We essentially have two tables:
        a) locmutation which stores the actual data
        b) opcodetype which implements and enforces the opcode enumeration type
        """
        conn = self.conn
        with conn:
            conn.execute("""
            CREATE TABLE locmutation(
            itemId  INTEGER PRIMARY KEY NOT NULL,
            time TIMESTAMP NOT NULL,
            oldLocId INTEGER NOT NULL,
            newLocId INTEGER,
            opcode CHAR(1) NOT NULL REFERENCES opcodetype(opcode));""")

        with conn:
            conn.execute("""
            CREATE TABLE opcodetype (
            opcode CHAR(1) PRIMARY KEY NOT NULL,
            Seq INTEGER UNIQUE NOT NULL);""")
        # we must switch the foreign_keys on, because the default is off in sqlite3.
        # we need them on in order to ensure that only valid opcodes are entered
        # in the tables.
        with conn:
            conn.execute("PRAGMA foreign_keys = on;")

        for opnum, opcode in enumerate(LocChange.valid_opcode_lst):
            with conn:
                conn.execute("INSERT INTO opcodetype(opcode, Seq) VALUES (?, ?);", (opcode, opnum))

    def _simple_add_location_change(self, l: LocChange) -> None:
        """Add a LocChange instance to the database.
        A RuntimeException is raised if a change with the same itemId already exists.
        """
        conn = self.conn
        tt = (l.itemid, l.ts, l.oldlocid, l.newlocid, l.opcode)
        try:
            with conn:
                conn.execute("""
                insert into locmutation(itemId, time, oldLocId, newLocId, opcode)
                values (?,?,?,?,?)""", tt)
        except sqlite3.IntegrityError as e:
            raise RuntimeError("add_loc failed: {}".format(e))

    def get_location_change(self, itemId: itemidtype) -> typing.Optional[LocChange]:
        """Retrieve a LocChange with the provided itemId.
        Return None if no record is found.
        """
        c = self.conn.cursor()
        c.execute("SELECT * FROM locmutation WHERE itemId=?", (itemId, ))
        rows = c.fetchall()
        print("BLA {}".format(rows))
        if len(rows) != 1:
            return None
        else:
            rr = rows[0]
            return LocChange(*rr)

    def get_all_location_changes(self) -> typing.List[LocChange]:
        """Retrieve all location changes in the database as a list of items.
        """
        c = self.conn.cursor()
        return [LocChange(*row) for row in c.execute("SELECT * FROM locmutation")]

    def add_location_change(self, l: LocChange) -> None:
        """Add a location change to the database.
        If a change already exists with the itemid, it will be overwritten.
        """
        conn = self.conn
        tt = (l.itemid, l.ts, l.oldlocid, l.newlocid, l.opcode)
        try:
            with conn:
                conn.execute("""
                  WITH newrec (itemId, time, oldLocId, newLocId, opcode) AS (VALUES(?,?,?,?,?) )
  INSERT OR REPLACE INTO locmutation(itemId, time, oldLocId, newLocId, opcode)
  SELECT newrec.itemId, newrec.time, newrec.oldLocId, newrec.newLocId, newrec.opcode
                FROM newrec LEFT JOIN locmutation AS oldrec ON newrec.itemId = oldrec.itemId;""",
                             tt)
        except sqlite3.IntegrityError as e:
            raise RuntimeError("add failed: {}".format(e))
