"""A module to manage a local copy of the QAI reagent database
using sqlite3 https://www.sqlite.org/index.html
and sqlalchemy  https://www.sqlalchemy.org/  .
"""

import typing
import logging

import hashlib
import json
import datetime
import sqlalchemy as sql
import sqlalchemy.orm as orm
from sqlalchemy.ext.declarative import declarative_base

import serverlib.timelib as timelib
import serverlib.serverconfig as serverconfig
import serverlib.yamlutil as yamlutil
import serverlib.qai_helper as qai_helper


logger = logging.Logger('ChemStock')

STATE_DIR_ENV_NAME = serverconfig.STATE_DIR_ENV_NAME


QAI_dct = typing.Dict[str, typing.Any]

Base = declarative_base()


def do_hash(dat: typing.Any) -> str:
    """Calculate a hash function of a data structure.

    This routine works by converting a data structure to a json string,
    then applying the SHA1 algorithm.
    Finally, the hexdigest is returned.

    Attention:
       Because conversion to json is involved, only serialisable data structures
       can be input.
    Note:
       In this routine, crucially,  keys are sorted in dicts when converting
       to json.  This ensures that identical dicts created
       differently (adding elements in a different order)
       produce the same hash.

    Args:
       dat: A serialisable python data structure to calculate the hash of.
    Returns:
       A string representing a hash function.
    """
    return hashlib.sha1(json.dumps(dat, sort_keys=True).encode('utf-8')).hexdigest()


class Reagent(Base):
    """A class describing a reagent."""
    __tablename__ = 'reagents'

    id = sql.Column(sql.Integer, primary_key=True)
    name = sql.Column(sql.String)
    basetype = sql.Column(sql.String)
    catalog_number = sql.Column(sql.String)
    category = sql.Column(sql.String)
    date_msds_expires = sql.Column(sql.String)
    # disposed = sql.Column(sql.Boolean)
    disposed = sql.Column(sql.String)
    expiry_time = sql.Column(sql.Integer)
    hazards = sql.Column(sql.String)
    # location = sql.Column(sql.String)
    msds_filename = sql.Column(sql.String)
    needs_validation = sql.Column(sql.String)
    notes = sql.Column(sql.String)
    qcs_document_id = sql.Column(sql.Integer)
    storage = sql.Column(sql.String)
    # supplier = sql.Column(sql.String)
    supplier_company_id = sql.Column(sql.Integer)

# {basetype: stockchem, catalog_number: TDF, category: Antiviral drugs/stds, date_msds_expires: null,
#  disposed: t, expiry_time: 2555, hazards: null, id: 6371, location: 605 dessicator,
#  msds_filename: null, name: Tenofovir Tablet, needs_validation: null, notes: null,
#  qcs_document_id: null, storage: Room Temperature, supplier: Pharmacy}


class Location(Base):
    """A class describing a physical location at which reagent items are stored."""
    __tablename__ = 'locations'

    id = sql.Column(sql.Integer, primary_key=True)
    name = sql.Column(sql.String)


class Reagent_Item(Base):
    __tablename__ = 'reagent_item'
    id = sql.Column(sql.Integer, primary_key=True)
    last_seen = sql.Column(sql.String)
    lot_num = sql.Column(sql.String)
    notes = sql.Column(sql.String)

    qcs_location_id = sql.Column(sql.Integer)
    qcs_reag_id = sql.Column(sql.Integer)
    rfid = sql.Column(sql.String)

# {id: 10155, last_seen: null, lot_num: 036P062593Anov06, notes: null, qcs_location_id: 10009,
#  qcs_reag_id: 566, rfid: ID123}


class Reagent_Item_Composition(Base):
    """A class describing the composition of a reagent item."""
    __tablename__ = 'reag_item_comp'

    id = sql.Column(sql.Integer, primary_key=True)
    src_item_id = sql.Column(sql.Integer)
    sub_item_id = sql.Column(sql.Integer)


class Reagent_Item_Status(Base):
    """A class describing the status of a reagent item."""
    __tablename__ = 'reag_item_status'

    id = sql.Column(sql.Integer, primary_key=True)
    occurred = sql.Column(sql.String)
    qcs_reag_item_id = sql.Column(sql.Integer)
    qcs_user_id = sql.Column(sql.Integer)
    status = sql.Column(sql.String)
    qcs_validation_id = sql.Column(sql.Integer)

# {id: 10220, occurred: '2011-09-30T00:00:00Z', qcs_reag_item_id: 10063, qcs_user_id: 10000,
#  status: USED_UP}


class User(Base):
    """A class describing a QAI user."""
    __tablename__ = 'users'

    id = sql.Column(sql.Integer, primary_key=True)
    email = sql.Column(sql.String)
    initials = sql.Column(sql.String)
    login = sql.Column(sql.String)

# {email: wscott@cfenet.ubc.ca, id: 10018, initials: WS, login: wscott}


class TimeUpdate(Base):
    """A class describing a time a database table was updated"""
    __tablename__ = "lastupdate"
    id = sql.Column(sql.Integer, primary_key=True)
    # dt = sql.Column(sql.TIMESTAMP(timezone=True), default=datetime.datetime.utcnow)
    dt = sql.Column(sql.TIMESTAMP(timezone=True), default=timelib.utc_nowtime)


class TableChange(Base):
    """For each table define in this module, keep a time-stamp of when it was
    last updated on the QAI server.
    This information is used to efficiently update only those tables that need updating.
    """
    __tablename__ = 'tabchange'
    table_name = sql.Column(sql.String, primary_key=True)
    stamp = sql.Column(sql.String)


class Locmutation(Base):
    """A class to keep track of a change in location of a reagent item:
    When stock taking, keep track of RFID's that have changed position.
    """
    __tablename__ = 'locmutation'

    VALID_OPS = frozenset(['missing', 'found', 'moved'])

    reag_item_id = sql.Column(sql.Integer, primary_key=True)
    locid = sql.Column(sql.Integer)
    # rfid = sql.Column(sql.String)
    op = sql.Column(sql.String)
    # ignore flag: the user can, upon verification, choose to ignore a location change
    # before it is uploaded to QAI
    ignore = sql.Column(sql.Boolean, default=False, nullable=False)
    # keep track of when the location change was recorded on the laptop
    # created_at = sql.Column(sql.TIMESTAMP(timezone=True), default=timelib.utc_nowtime)


class node:
    """An internal helper class used to sort the hierarchical location names."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.child_dct: typing.Dict[str, "node"] = {}
        self.val: typing.Optional[dict] = None

    def addtree(self, dct) -> None:
        """Add a location dictionary to a leaf in the tree based on its
        hierarchical name."""
        namelst = dct['name'].split('\\')
        # print('nlst {}'.format(namelst))
        nn = self
        for curname in namelst:
            nextlevel = nn.child_dct.get(curname, None)
            if nextlevel is None:
                nextlevel = nn.child_dct[curname] = node(curname)
            nn = nextlevel
        nn.setval(dct)

    def setval(self, newval) -> None:
        if self.val is None:
            self.val = newval
        else:
            raise RuntimeError('node value set twice!')

    def getval(self) -> typing.Optional[dict]:
        return self.val

    def dfslst(self, topname, lst) -> None:
        fullname = "{}.{}".format(topname, self.name)
        val = self.getval()
        if val is not None:
            lst.append(val)
        for child in sorted(self.child_dct.values(), key=lambda a: a.name):
            child.dfslst(fullname, lst)


def sortloclist(orglst: typing.List[dict]) -> typing.List[dict]:
    """Sort the list of location dicts in a hierarchically sensible order.

    The method applied is the following: Nodes are added to a tree based on name,
    then an in-order DFS traversal is performed (children are sorted alphabetically)
    to sort the list.

    Args:
       orglst: the original, unsorted list of location dicts
    Returns:
       A copy of the input list sorted according to hierarchical location.
    """
    root = node('')
    for dct in orglst:
        root.addtree(dct)
    rlst: typing.List[dict] = []
    root.dfslst("", rlst)
    return rlst


LocChangeTup = typing.Tuple[int, str]
LocChangeList = typing.List[LocChangeTup]


class ChemStockDB:
    """ Maintain a local copy of the QAI chemical stock program."""

    _ITM_LIST = [(qai_helper.QAISession.QAIDCT_LOCATIONS, Location),
                 (qai_helper.QAISession.QAIDCT_USERS, User),
                 (qai_helper.QAISession.QAIDCT_REAITEM_COMPOSITION, Reagent_Item_Composition),
                 (qai_helper.QAISession.QAIDCT_REAGENTS, Reagent),
                 (qai_helper.QAISession.QAIDCT_REAGENT_ITEMS, Reagent_Item),
                 (qai_helper.QAISession.QAIDCT_REAITEM_STATUS, Reagent_Item_Status)]

    _not_write_set = frozenset([('moved', 'missing'), ('missing', 'missing'),
                                ('found', 'missing')])

    def __init__(self,
                 locQAIfname: typing.Optional[str],
                 qaisession: typing.Optional[qai_helper.QAISession],
                 tz_name: str) -> None:
        """
        This database is accessed by the stocky web server.
        It is passed a :class:`qai_helper.QAISession` instance which it
        uses to access the QAI database via an HTTP API.
        This stock information is stored to a local file locQAIfname as an sqlite3 database
        in the server state directory if a name is provided. Otherwise it is stored in memory.

        Args:
           locQAIfname: the name of the file which is used to store the database information
            by sqlite. If this is None, the database is stored in memory (This is used mostly
            for testing).
           qaisession: the session instance used to access the QAI server.
           tz_name: the name of the local timezone.
        """
        self.qaisession = qaisession
        if locQAIfname is None:
            db_name = 'sqlite://'
            self._locQAIfname = None
        else:
            actual_filename = yamlutil.get_filename(locQAIfname, STATE_DIR_ENV_NAME)
            db_name = 'sqlite:///%s' % actual_filename
            self._locQAIfname = actual_filename
        self._engine = sql.create_engine(db_name)
        Base.metadata.create_all(self._engine)
        Session = orm.sessionmaker(bind=self._engine)
        timelib.set_local_timezone(tz_name)
        self._current_date = timelib.loc_nowtime().date()
        self._sess = Session()
        self._haschanged = True
        self.generate_webclient_stocklist()

    def _set_update_time(self) -> str:
        """Set the ChemDB update time to now
        and return the current datetime as a string.
        """
        s = self._sess
        tt = s.query(TimeUpdate).first()
        if tt is None:
            # make a new record
            tt = TimeUpdate(id=99)
            s.add(tt)
            s.commit()
        else:
            # tt.dt = datetime.datetime.utcnow()
            tt.dt = timelib.utc_nowtime()
            s.merge(tt)
            s.commit()
        return self.get_update_time()

    def get_update_time(self) -> str:
        """Return the ChemDB update time.

        The update time is the last time the local ChemDB was updated from
        the QAI server.

        Returns:
           The time as a string. Return 'never' if the database is empty.
        """
        s = self._sess
        tt = s.query(TimeUpdate).first()
        if tt is None:
            return 'never'
        else:
            return timelib.datetime_to_str(tt.dt, in_local_tz=True)

    def get_db_stats(self) -> typing.Dict[str, int]:
        """Return database size statistics.

        Return the number of records we have in each database table.

        Returns:
           The keys are table names, the values are the number of records in each table.
        """
        s = self._sess
        rdct = {}
        for idname, classname in ChemStockDB._ITM_LIST:
            rdct[idname] = s.query(classname).count()
        return rdct

    def update_from_QAI(self) -> dict:
        """Update the local ChemStock using the qaisession.
           Returns:
              A dict describing what happened (success, error messages)
        """
        qaisession = self.qaisession
        if qaisession is None or not qaisession.is_logged_in():
            return dict(ok=False, msg="User not logged in")
        # get the locally stored timestamp data from our database
        cur_tsdata = self.load_TS_data()
        try:
            newds = qai_helper.QAIDataset(None, cur_tsdata)
        except RuntimeError as e:
            return dict(ok=False, msg="QAI access error: {}".format(str(e)))
        # load those parts from QAI that are out of date
        update_dct = qaisession.clever_update_QAI_dump(newds)
        # if any value is True, then we did get something from QAI...
        num_updated = sum(update_dct.values())
        if num_updated > 0:
            try:
                self._haschanged = self.loadQAI_data(newds, update_dct)
            except TypeError as e:
                return dict(ok=False, msg="database error: {}".format(str(e)))
        return dict(ok=True, msg="Successfully updated {} tables for QAI".format(num_updated))

    def loadQAI_data(self,
                     qaiDS: qai_helper.QAIDataset,
                     update_dct: typing.Optional[qai_helper.QAIUpdatedct] = None) -> bool:
        """Replace the database contents with the data contained in qaiDS
        if update_dct is provided, only update those tables for which
        update_dct[idname] is True.
        Return := 'the update was successful'
        """
        s = self._sess
        # first, add the data....
        qaidct = qaiDS.get_data()
        upd_dct = update_dct or {}
        for idname, classname in ChemStockDB._ITM_LIST:
            do_msg = True
            do_update = upd_dct.get(idname, True)
            if do_update:
                # first, empty the table, then reload from scratch
                s.query(classname).delete()
                s.commit()
                # get the column names defined in this table
                kset = set(classname.__table__.columns.keys())
                for r_dct in qaidct[idname]:
                    got_keys = set(r_dct.keys())
                    unwanted_keys = got_keys - kset
                    if do_msg and len(unwanted_keys) > 0:
                        logger.warning("class {}: QAI provided unwanted keys {}".format(classname, unwanted_keys))
                    for k in unwanted_keys:
                        del r_dct[k]
                    if do_msg:
                        missing_keys = kset - got_keys
                        if len(missing_keys) > 0:
                            logger.warning("class {}: missing keys {}".format(classname, missing_keys))
                    # print("BLA {}".format(r_dct))
                    s.add(classname(**r_dct))
                    do_msg = False
                s.commit()
        # now add the timestamps
        tsdct = qaiDS.get_timestamp()
        for k, val in tsdct.items():
            do_update = upd_dct.get(k, True)
            if do_update:
                tc = TableChange(**dict(table_name=k, stamp=val))
                s.merge(tc)
        s.commit()
        self._set_update_time()
        return True

    def load_TS_data(self) -> qai_helper.QAIChangedct:
        """Retrieve the current timestamp data from the database."""
        rdct: qai_helper.QAIChangedct = {}
        for tc in self._sess.query(TableChange):
            rdct[tc.table_name] = tc.stamp
        # make sure we have all required keys set to a value...
        for k in qai_helper.QAISession.qai_key_lst:
            rdct.setdefault(k, None)
        return rdct

    def calc_final_state(self, slst: typing.List[dict]) -> typing.Tuple[dict, bool, bool]:
        """ Calculate the final state from this list of states.
        We return the nominal state record and two booleans:
        ismissing, hasexpired.

        Strategy: we assign values to the various possible states and sort according
        to these values.
        Any missing record will be the first one.
        The exp record is the last one (should exist, check the date with current date)
        The nominal state is the second to last in the list.
        """
        if len(slst) < 2:
            # raise RuntimeError("state list is too short {}".format(slst))
            # the list may also contain a single EXPIRED record
            # or, in legacy cases, a single IN_USE record.
            nom_state = exp_dict = slst[0]
            ismissing = False
            # if exp_dict['status'] != 'EXPIRED':
            #    raise RuntimeError('exp_dict is not expired {}'.format(exp_dict))
        else:
            odct = dict(MISSING=-1, MADE=0, VALIDATED=1, IN_USE=2,
                        USED_UP=5, EXPIRED=6, RUO_EXPIRED=7, DISPOSED=8)
            # create tuples of input dicts with scores from odct.
            try:
                plst = [(d, odct.get(d['status'], None)) for d in slst]
            except KeyError:
                raise RuntimeError("status field missing in state record {}".format(slst))
            qlst = [tt for tt in plst if tt[1] is not None]
            qlst.sort(key=lambda a: a[1])
            exp_dict = qlst[-1][0]
            nom_state = qlst[-2][0]
            ismissing = qlst[0][0]['status'] == 'MISSING'
        # we could have no expired record, but a used up record instead.
        exp_state = exp_dict.get('status', None)
        if exp_state is None:
            raise RuntimeError("status field missing in state record {}".format(exp_dict))
        elif exp_state == 'EXPIRED':
            # Cannot use fromisoformat in 3.6...
            # expiry_date = datetime.date.fromisoformat(exp_dict['occurred'])
            # the string is of the form '2011-04-20'
            expiry_date = datetime.date(*[int(s) for s in exp_dict['occurred'].split('-')])
            has_expired = expiry_date < self._current_date
        else:
            has_expired = False
        # print("FFF {}".format(slst))
        rtup = (nom_state, ismissing, has_expired)
        # print("GGG {}".format(rtup))
        return rtup

    def DOgenerate_webclient_stocklist(self) -> dict:
        """Generate the stock list in a form required by the web client.

        Returns:
        The dict returned has the following entries:
        loclst: a list of dicts containing the stock locations, e.g.

           [{'id': 10000, 'name': 'SPH'}, {'id': 10001, 'name': 'SPH\\638'}, ... ]

        The itemlst is a list of dicts containing:

         {'id': 18478, 'last_seen': None, 'lot_num': '2019AD3EB',
            'notes': '8 bottles of spare reagents',
            'qcs_location_id': 10010,
            'qcs_reag_id': 6297, 'rfid': 'REPLACE ME'},
         {'id': 18479, 'last_seen': None, 'lot_num': 'INT.BP.17.02',
            'notes': None, 'qcs_location_id': 10016,
            'qcs_reag_id': 6217, 'rfid': 'REPLACE ME'}

        The itmstatlst is a list of dicts containing:

          {'id': 41418, 'occurred': '2021-04-30T07:00:00Z',
            'qcs_reag_item_id': 18512, 'qcs_user_id': 113, 'status': 'EXPIRED'},
          {'id': 41419, 'occurred': '2018-06-01T22:54:26Z',
            'qcs_reag_item_id': 18513, 'qcs_user_id': 112, 'status': 'MADE'},
          {'id': 41420, 'occurred': '2020-04-03T00:00:00Z',
            'qcs_reag_item_id': 18513, 'qcs_user_id': 112, 'status': 'EXPIRED'}

        The reagentlst is a list of dicts containing:

          {'id': 8912, 'name': 'Atazanavir-bisulfate', 'basetype': 'reagent',
            'catalog_number': None, 'category': 'TDM', 'date_msds_expires': None,
            'disposed': None, 'expiry_time': None,
            'hazards': 'Avoid inhalation, skin and eye contact. Wear PPE.',
            'location': None, 'msds_filename': 'ATV_BS_A790050MSDS.pdf',
            'needs_validation': None, 'notes': None, 'qcs_document_id': None,
            'storage': '-20 C', 'supplier': None},
          {'id': 8932, 'name': 'Triton X-100', 'basetype': 'stockchem',
            'catalog_number': 'T8787', 'category': 'Other Chemicals',
            'date_msds_expires': '2020-02-28T00:00:00Z', 'disposed': None,
            'expiry_time': 2555, 'hazards': None, 'location': None,
            'msds_filename': None, 'needs_validation': None,
            'notes': None, 'qcs_document_id': None, 'storage': 'Room Temperature',
            'supplier': 'Sigma Aldrich'},
         {'id': 8952, 'name': 'Proviral V3 Primary 1st PCR  mix', 'basetype': 'reagent',
            'catalog_number': None, 'category': 'PCR',
            'date_msds_expires': None, 'disposed': None,
            'expiry_time': None, 'hazards': None,
            'location': '604', 'msds_filename': None,
            'needs_validation': None,
            'notes': None, 'qcs_document_id': None,
            'storage': '-20 C', 'supplier': None}

        """
        # NOTE: as we want dicts and not Location instances, we go directly to
        # the 'SQL level' (session.execute() and not the 'ORM level' (session.query())
        # of sqlquery.
        s = self._sess
        loclst = [dict(row) for row in s.execute(Location.__table__.select())]
        itmlst = [dict(row) for row in s.execute(Reagent_Item.__table__.select())]
        itmstat = [dict(row) for row in s.execute(Reagent_Item_Status.__table__.select())]

        # create a Dict[locationid, List[reagentitem]] and a Dict[RFID, reagentitem]
        dd: typing.Dict[typing.Optional[int], typing.List[dict]] = {}
        # rfid_reagitem_dct = ff = {}
        ff: typing.Dict[str, dict] = {}
        for reag_item in itmlst:
            loc_id = reag_item.get('qcs_location_id', None)
            # we will keep a list of items with None locations... should not happen, but does
            # then we add these to the UNKNOWN list later on
            dd.setdefault(loc_id, []).append(reag_item)
            # if loc_id is not None:
            # else:
            #    raise RuntimeError("found None location {}".format(reag_item))
            #
            rfidstr = reag_item.get('rfid', None)
            if rfidstr is not None:
                if rfidstr != 'REPLACE ME':
                    ff.setdefault(rfidstr, reag_item)
            else:
                raise RuntimeError("found None location {}".format(reag_item))
        # unmangling for None...
        # find loc_id for 'UNKNOWN'...
        if None in dd:
            none_lst = dd[None]
            del dd[None]
            flst = [loc for loc in loclst if loc['name'] == 'UNKNOWN']
            assert len(flst) == 1, "cannot determine 'UNKNOWN' location"
            unknown_lst = dd.setdefault(flst[0]['id'], [])
            unknown_lst.extend(none_lst)
        #
        # NOW, create a Dict[locationid, Tuple[locrecord, List[reagentitem]]]
        # which we send to the client
        rr: typing.Dict[int, typing.Tuple[dict, typing.List[dict]]] = {}
        locid_reagitem_dct = rr
        for location in loclst:
            loc_id = location.get('id', None)
            rr[loc_id] = (location, dd.get(loc_id, []))
        assert len(rr) == len(loclst), "problem with location ids!"
        #
        # collect the state records for each reagent item...
        zz: typing.Dict[int, list] = {}
        for state in itmstat:
            reag_item_id = state['qcs_reag_item_id']
            # we want to replace the occurred timedate entry with a simple date
            # to present to the user, i.e.
            # 'occurred': '2011-04-20T00:00:00Z'  -> '2011-04-20'
            dstr = state['occurred']
            state['occurred'] = dstr.split('T')[0]
            zz.setdefault(reag_item_id, []).append(state)
        # and evaluate the 'final state' for each reagent item
        ritemdct = {}
        for reag_item in itmlst:
            reag_item_id = reag_item['id']
            state_lst = zz.get(reag_item_id, None)
            if state_lst is None:
                state_info = None
            else:
                state_info = self.calc_final_state(state_lst)
                # print("BLAAA {} {}".format(reag_item_id, state_info))
                # we eliminate any reagent item that has a state of 'USED_UP'.
                dct, ismissing, hasexpired = state_info
                state_info = None if dct['status'] == 'USED_UP' else state_info
            if state_info is not None:
                ritemdct[reag_item_id] = (reag_item, state_info)
            # else:
            # print("skipping {}".format(reag_item))
        # create a Dict[reagentid, reagent]
        rl = [dict(row) for row in s.execute(Reagent.__table__.select())]
        rg = {}
        for reagent in rl:
            # delete the legacy location field in reagents...
            reagent.pop('location', None)
            reagent_id = reagent.get('id', None)
            if reagent_id is not None:
                rg[reagent_id] = reagent
            else:
                raise RuntimeError("reagent ID is None")
        assert len(rg) == len(rl), "problem with reagent ids!"
        # "itmstatlst": itmstat,
        # finally, sort the loclst according to a hierarchy
        loclst = sortloclist(loclst)
        return {"loclst": loclst, "locdct": locid_reagitem_dct,
                "ritemdct": ritemdct, "reagentdct": rg}
    # , "rfiddct": rfid_reagitem_dct}

    def generate_webclient_stocklist(self) -> dict:
        if self._haschanged:
            self._cachedct = self.DOgenerate_webclient_stocklist()
            self._haschanged = False
        return self._cachedct

    # location changes ---
    def reset_loc_changes(self) -> None:
        """Remove all location changes in the database.
        A location change occurs when, during stock taking, a reagent item was
        found in a location that does not agree with the database.
        The user enters a location change for that item to be uploaded
        to QAI at a later date.
        """
        s = self._sess
        s.query(Locmutation).delete()
        s.commit()

    def number_of_loc_changes(self) -> int:
        """Return the number of location changes currently in the database"""
        s = self._sess
        return s.query(Locmutation).count()

    def add_loc_changes(self, locid: int, locdat: LocChangeList) -> None:
        """Add a location change to the database.

        Any location mutation with an existing reagent_item id will be silently overwritten
        by any location id, and opstring. In addition, do_ignore will be set to False.

        Args:
           locid: the id of the new location of the reagent items in locdat
           locdat: a list of tuple with an reagent_item id (int) and an opstring (str)
           indicating the items to change the location of.
              (reagent item ID, string)
              For example: (18023, 'missing')
        Raises:
           ValueError: if the data types are not as expected.
        """
        # NOTE: type check all records before adding any records. In this way,
        # any type exception does no change the database.
        if not isinstance(locid, int):
            raise ValueError("locid must be an int")
        for reag_itm_id, opstring in locdat:
            if not isinstance(reag_itm_id, int):
                raise ValueError("reag_itm_id must be an int")
            if not isinstance(opstring, str):
                raise ValueError("opstring must be a string")
            if opstring not in Locmutation.VALID_OPS:
                raise ValueError("unknown opstring '{}', valid ops: {}".format(opstring,
                                                                               Locmutation.VALID_OPS))
        s = self._sess
        for reag_itm_id, opstring in locdat:
            # we overwrite any existing records with the same reag_item_id,
            # except in certain cases:
            # do_not_write = newloc_id != oldloc_id
            do_write = True
            if opstring == 'missing':
                my_locmut = s.query(Locmutation).filter(Locmutation.reag_item_id == reag_itm_id).first()
                if my_locmut is not None and locid != my_locmut.locid:
                    # we have a record, and the location is different. Now decide whether
                    # we should overwrite the record or not based on (old_op, new_op) pair.
                    do_write = (my_locmut.op, opstring) not in self._not_write_set
            if do_write:
                lm = Locmutation(**dict(reag_item_id=reag_itm_id,
                                        locid=locid,
                                        op=opstring,
                                        ignore=False))
                s.merge(lm)

    def set_ignore_flag(self, reag_item_id: int, do_ignore: bool) -> dict:
        """Set/reset the ignore location change flag.

        Args:
           reag_item_id: the reagent item with a location change
           do_ignore: set this to True (the location change is ignored) or False
        Returns:
           A dict with a response that can be sent back to the webclient for diagnostics.
           The dict will have an 'ok' boolean entry, and a 'msg' string entry.
        """
        if not isinstance(reag_item_id, int):
            raise ValueError("reag_item_id must be an int")
        if not isinstance(do_ignore, bool):
            raise ValueError("do_ignore must be a bool")
        s = self._sess
        locmut = s.query(Locmutation).filter_by(reag_item_id=reag_item_id).first()
        if locmut is None:
            retdct = dict(ok=False,
                          msg="no locmutation record for reag_item_id={}".format(reag_item_id))
        else:
            locmut.ignore = do_ignore
            s.commit()
            retdct = dict(ok=True, msg="record successfully updated")
        return retdct

    def get_loc_changes(self, oldhash: typing.Optional[str] = None) -> \
            typing.Tuple[str, typing.Optional[typing.Dict[int, LocChangeList]]]:
        """Return all location changes in the database.

        Args:
           oldhash: an optional hashkey indicating the last retrieved database state.
        Returns:
           If oldhash does not match our current hash,
           return the new hash and a new dictionary.
           The dictionary keys are location id's, and the values are a list of tuples.
           The tuples are of the form (reagent item id, operation string,
                                       row id, row ignore boolean)
           If the hash does match, return the newhash and None. In this case, the stocky server
           will know that the webclient already has an a up-to-date version of the location changes.
        """
        oldhash = oldhash or ""
        ret_dct: typing.Dict[int, LocChangeList] = {}
        # NOTE: we sort by reag_item_id in order to make hashing reproducible.
        for row in self._sess.execute(Locmutation.__table__.select().order_by(Locmutation.reag_item_id)):
            # time_str = timelib.datetime_to_str(row.created_at, in_local_tz=True)
            ret_dct.setdefault(row.locid, []).append((row.reag_item_id,
                                                      row.op,
                                                      row.ignore))
            # time_str))
        newhash = do_hash(ret_dct)
        if oldhash != newhash:
            return newhash, ret_dct
        else:
            return newhash, None
