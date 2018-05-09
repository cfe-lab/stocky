
import sqlite3
import datetime

# string of length 1
opcodetype = str

datetimetype = datetime.datetime

locidtype = int


class LocChange:
    def __init__(self, itemid: int, timestamp: datetimetype,
                 oldlocid: locidtype, newlocid: locidtype,
                 opcode: str) -> None:
        self.itemid = itemid
        self.ts = timestamp
        self.oldlocid = oldlocid
        self.newlocid = newlocid
        self.opcode = opcode


class LocChangeList:

    confirmLocation = 'O'
    markMissing = 'M'
    changeLocation = 'C'

    def __init__(self, fname: str=None) -> None:
        """Initialise an empty location change file.
        if fname is None, then create a db in memory.
        """
        ff = fname or ':memory:'
        self.conn = sqlite3.connect(ff, detect_types=sqlite3.PARSE_DECLTYPES)
        # self.cur = self.conn.cursor()
        self.initdb()

    def initdb(self):
        """Create a table with the required columns"""
        conn = self.conn
        with conn:
            conn.execute("""
            CREATE TABLE locmutation(
            itemId  INTEGER PRIMARY KEY NOT NULL,
            time TIMESTAMP,
            oldLocId INTEGER NOT NULL,
            newLocId INTEGER,
            opcode CHAR(1) NOT NULL REFERENCES opcodetype(opcode));""")

        with conn:
            conn.execute("""
            CREATE TABLE opcodetype (
            opcode CHAR(1) PRIMARY KEY NOT NULL,
            Seq INTEGER);""")
        with conn:
            conn.execute("INSERT INTO opcodetype(opcode, Seq) VALUES ('O', 1);")
        with conn:
            conn.execute("INSERT INTO opcodetype(opcode, Seq) VALUES ('M', 2);")
        with conn:
            conn.execute("INSERT INTO opcodetype(opcode, Seq) VALUES ('C', 3);")

    def add_location_change(self, l: LocChange) -> None:
        conn = self.conn
        tt = (l.itemid, l.ts, l.oldlocid, l.newlocid, l.opcode)
        try:
            with conn:
                conn.execute("""
                insert into locmutation(itemId, time, oldLocId, newLocId, opcode)
                values (?,?,?,?,?)""", tt)
        except sqlite3.IntegrityError as e:
            raise RuntimeError("add_loc failed: {}".format(e))
