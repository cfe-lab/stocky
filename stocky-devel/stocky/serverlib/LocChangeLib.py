
import sqlite3
import datetime

# string of length 1
opcodetype = str

datetimetype = datetime.datetime

locidtype = int
itemidtype = int


class LocChange:
    confirmLocation = 'O'
    markMissing = 'M'
    changeLocation = 'C'

    valid_opcode_lst = [confirmLocation, markMissing, changeLocation]
    valid_opcode_set = frozenset(valid_opcode_lst)

    def __init__(self, itemid: itemidtype, timestamp: datetimetype,
                 oldlocid: locidtype, newlocid: locidtype,
                 opcode: opcodetype) -> None:
        self.itemid = itemid
        self.ts = timestamp
        self.oldlocid = oldlocid
        self.newlocid = newlocid
        self.opcode = opcode

    def __str__(self) -> str:
        return "{} {} {} {} {}".format(self.itemid, self.ts, self.oldlocid,
                                       self.newlocid, self.opcode)

    def __eq__(self, ot) -> bool:
        """We have to imple,ment the == operator so that we can check for
        equivalence in the tests.
        """
        return self.itemid == ot.itemid and \
            self.ts == ot.ts and \
            self.oldlocid == ot.oldlocid and \
            self.newlocid == ot.newlocid and \
            self.opcode == ot.opcode

    def has_valid_opcode(self) -> bool:
        return self.opcode in LocChange.valid_opcode_set


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

    def get_location_change(self, itemId: itemidtype) -> LocChange:
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
