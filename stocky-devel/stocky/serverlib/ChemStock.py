"""A module to manage a local copy of the QAI reagent database
using sqlite3 https://www.sqlite.org/index.html
and sqlalchemy  https://www.sqlalchemy.org/  .
"""

import typing
import logging

import sqlalchemy as sql
import sqlalchemy.orm as orm
from sqlalchemy.ext.declarative import declarative_base

import serverlib.chemdb as chemdb
import serverlib.timelib as timelib
import serverlib.serverconfig as serverconfig
import serverlib.yamlutil as yamlutil
import serverlib.qai_helper as qai_helper


logger = logging.Logger('ChemStock')

STATE_DIR_ENV_NAME = serverconfig.STATE_DIR_ENV_NAME


Base = declarative_base()


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


class LocMutation(chemdb.BaseLocMutation, Base):
    """A class to keep track of a change in location of a reagent item:
    When stock taking, keep track of reagent+items that have changed position.
    """
    __tablename__ = 'locmutation'

    reag_item_id = sql.Column(sql.Integer, primary_key=True)
    locid = sql.Column(sql.Integer)
    # rfid = sql.Column(sql.String)
    op = sql.Column(sql.String)
    # ignore flag: the user can, upon verification, choose to ignore a location change
    # before it is uploaded to QAI
    ignore = sql.Column(sql.Boolean, default=False, nullable=False)
    # keep track of when the location change was recorded on the laptop
    # created_at = sql.Column(sql.TIMESTAMP(timezone=True), default=timelib.utc_nowtime)
    #
    # whether this LocMutation has been successfully reported to QAI
    sent_to_qai = sql.Column(sql.Boolean, default=False, nullable=False)


class ChemStockDB(chemdb.BaseDB):
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
        super().__init__(qaisession, tz_name)
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
        self._sess = Session()
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

    def load_qai_data(self,
                      qai_ds: qai_helper.QAIDataset,
                      update_dct: typing.Optional[qai_helper.QAIUpdatedct] = None) -> bool:
        """Replace the database contents with the data contained in qai_ds
        if update_dct is provided, only update those tables for which
        update_dct[idname] is True.
        Return := 'the update was successful'
        """
        s = self._sess
        # first, add the data....
        qaidct = qai_ds.get_data()
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
        tsdct = qai_ds.get_timestamp()
        for k, val in tsdct.items():
            do_update = upd_dct.get(k, True)
            if do_update:
                tc = TableChange(**dict(table_name=k, stamp=val))
                s.merge(tc)
        s.commit()
        self._set_update_time()
        return True

    def get_ts_data(self) -> qai_helper.QAIChangedct:
        """Retrieve the current timestamp data from the database."""
        rdct: qai_helper.QAIChangedct = {}
        for tc in self._sess.query(TableChange):
            rdct[tc.table_name] = tc.stamp
        # make sure we have all required keys set to a value...
        for k in qai_helper.QAISession.qai_key_lst:
            rdct.setdefault(k, None)
        return rdct

    def get_location_list(self) -> chemdb.DBRecList:
        """Return a list of all defined locations."""
        s = self._sess
        return [dict(row) for row in s.execute(Location.__table__.select())]

    def get_reagent_list(self) -> chemdb.DBRecList:
        """Return a list of all reagents."""
        s = self._sess
        return [dict(row) for row in s.execute(Reagent.__table__.select())]

    def get_reagent_item_list(self) -> chemdb.DBRecList:
        """Return a list of all reagent items."""
        s = self._sess
        return [dict(row) for row in s.execute(Reagent_Item.__table__.select())]

    def get_reagent_item_status_list(self) -> chemdb.DBRecList:
        """Return a list of all reagent item statuses."""
        s = self._sess
        return [dict(row) for row in s.execute(Reagent_Item_Status.__table__.select())]

    # location changes ---
    def reset_loc_changes(self) -> None:
        """Remove all location changes in the database.
        A location change occurs when, during stock taking, a reagent item was
        found in a location that does not agree with the database.
        The user enters a location change for that item to be uploaded
        to QAI at a later date.
        """
        s = self._sess
        s.query(LocMutation).delete()
        s.commit()

    def number_of_loc_changes(self) -> int:
        """Return the number of location changes currently in the database"""
        s = self._sess
        return s.query(LocMutation).count()

    def add_loc_changes(self, locid: int, locdat: chemdb.LocChangeList) -> None:
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
        self._verify_loc_changes(locid, locdat)
        s = self._sess
        for reag_itm_id, opstring in locdat:
            # we overwrite any existing records with the same reag_item_id,
            # except in certain cases.
            do_write = True
            if opstring == 'missing':
                my_locmut = s.query(LocMutation).filter(LocMutation.reag_item_id == reag_itm_id).first()
                if my_locmut is not None and locid != my_locmut.locid:
                    # we have a record, and the location is different. Now decide whether
                    # we should overwrite the record or not based on (old_op, new_op) pair.
                    do_write = (my_locmut.op, opstring) not in self._not_write_set
            if do_write:
                lm = LocMutation(**dict(reag_item_id=reag_itm_id,
                                        locid=locid,
                                        op=opstring,
                                        ignore=False))
                s.merge(lm)
        s.commit()

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
        locmut = s.query(LocMutation).filter_by(reag_item_id=reag_item_id).first()
        if locmut is None:
            retdct = dict(ok=False,
                          msg="no locmutation record for reag_item_id={}".format(reag_item_id))
        else:
            locmut.ignore = do_ignore
            s.commit()
            retdct = dict(ok=True, msg="record successfully updated")
        return retdct

    def get_loc_changes(self, oldhash: typing.Optional[str] = None) -> \
            typing.Tuple[str, typing.Optional[typing.Dict[int, chemdb.LocChangeList]]]:
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
        ret_dct: typing.Dict[int, chemdb.LocChangeList] = {}
        # NOTE: we sort by reag_item_id in order to make hashing reproducible.
        for row in self._sess.execute(LocMutation.__table__.select().order_by(LocMutation.reag_item_id)):
            # time_str = timelib.datetime_to_str(row.created_at, in_local_tz=True)
            ret_dct.setdefault(row.locid, []).append((row.reag_item_id,
                                                      row.op,
                                                      row.ignore))
            # time_str))
        newhash = chemdb.do_hash(ret_dct)
        if oldhash != newhash:
            return newhash, ret_dct
        else:
            return newhash, None

    def perform_loc_changes(self, move_dct: dict) -> dict:
        """
         * Report the required changes from the list provided to QAI.
         * Update the local LocMutation table accordingly
         * Purge successfully recorded locmutations
         * Replenish our DB from QAI.
         * Return a dict in response (success/failure)
        """
        res = self._report_loc_changes(move_dct)
        # now purge all records that are marked as sent_to_qai.
        s = self._sess
        s.query(LocMutation).filter_by(sent_to_qai=True).delete()
        s.commit()
        return res

    def _report_loc_changes(self, move_dct: dict) -> dict:
        """Report all location changes in the local database to QAI.
        If a an individual location change was successfully recorded with QAI,
        then mark the sent_to_qai field of the record.
        This will allows us to delete all successfully reported changes.

        If an error occurs in any of the qai interactions, then a dict containing ok=False
        is returned.
        """
        qaisession = self.qaisession
        s = self._sess
        print("PERFORM LOC_CHANGE")
        for locid_string, mvlst in move_dct.items():
            locid = int(locid_string)
            print("LOCID {}".format(locid))
            for reag_item_id, opstring, do_ignore in mvlst:
                if isinstance(reag_item_id, str):
                    # print('stringy {}'.format(reag_item_id))
                    reag_item_id = int(reag_item_id)
                print("   mm {} {} {}".format(reag_item_id, opstring, do_ignore))
                if not do_ignore:
                    locmut = s.query(LocMutation).filter_by(reag_item_id=reag_item_id).first()
                    if locmut is None:
                        return dict(ok=False,
                                    msg="no locmutation record for reag_item_id={}".format(reag_item_id))
                    resdct = qaisession.report_item_location(reag_item_id, locid, opstring)
                    is_ok = resdct.get('ok', False)
                    if is_ok:
                        locmut.sent_to_qai = True
                        s.commit()
                    else:
                        return resdct
        return dict(res='ok')
