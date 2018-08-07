
# A module to manage a local copy of the reagent database using sqlite3 and sqlalchemy

import typing
import logging

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


class Reagent(Base):
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
    location = sql.Column(sql.String)
    msds_filename = sql.Column(sql.String)
    needs_validation = sql.Column(sql.String)
    notes = sql.Column(sql.String)
    qcs_document_id = sql.Column(sql.Integer)
    storage = sql.Column(sql.String)
    supplier = sql.Column(sql.String)

# {basetype: stockchem, catalog_number: TDF, category: Antiviral drugs/stds, date_msds_expires: null,
#  disposed: t, expiry_time: 2555, hazards: null, id: 6371, location: 605 dessicator,
#  msds_filename: null, name: Tenofovir Tablet, needs_validation: null, notes: null,
#  qcs_document_id: null, storage: Room Temperature, supplier: Pharmacy}


class Location(Base):
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
    __tablename__ = 'reag_item_comp'

    id = sql.Column(sql.Integer, primary_key=True)
    src_item_id = sql.Column(sql.Integer)
    sub_item_id = sql.Column(sql.Integer)


class Reagent_Item_Status(Base):
    __tablename__ = 'reag_item_status'

    id = sql.Column(sql.Integer, primary_key=True)
    occurred = sql.Column(sql.String)
    qcs_reag_item_id = sql.Column(sql.Integer)
    qcs_user_id = sql.Column(sql.Integer)
    status = sql.Column(sql.String)

# {id: 10220, occurred: '2011-09-30T00:00:00Z', qcs_reag_item_id: 10063, qcs_user_id: 10000,
#  status: USED_UP}


class User(Base):
    __tablename__ = 'users'

    id = sql.Column(sql.Integer, primary_key=True)
    email = sql.Column(sql.String)
    initials = sql.Column(sql.String)
    login = sql.Column(sql.String)

# {email: wscott@cfenet.ubc.ca, id: 10018, initials: WS, login: wscott}


class TimeUpdate(Base):
    __tablename__ = "lastupdate"
    id = sql.Column(sql.Integer, primary_key=True)
    # dt = sql.Column(sql.TIMESTAMP(timezone=True), default=datetime.datetime.utcnow)
    dt = sql.Column(sql.TIMESTAMP(timezone=True), default=timelib.utc_nowtime)


# for each table above, keep a time-stamp of when it was last updated on the QAI server.
class TableChange(Base):
    __tablename__ = 'tabchange'
    table_name = sql.Column(sql.String, primary_key=True)
    stamp = sql.Column(sql.String)


class ChemStockDB:

    _ITM_LIST = [(qai_helper.QAISession.QAIDCT_LOCATIONS, Location),
                 (qai_helper.QAISession.QAIDCT_USERS, User),
                 (qai_helper.QAISession.QAIDCT_REAITEM_COMPOSITION, Reagent_Item_Composition),
                 (qai_helper.QAISession.QAIDCT_REAGENTS, Reagent),
                 (qai_helper.QAISession.QAIDCT_REAGENT_ITEMS, Reagent_Item),
                 (qai_helper.QAISession.QAIDCT_REAITEM_STATUS, Reagent_Item_Status)]

    def __init__(self,
                 locQAIfname: typing.Optional[str],
                 qaisession: typing.Optional[qai_helper.QAISession],
                 tz_name: str) -> None:
        """
        This stock information is stored to a local file locQAIfname as an sqlite3 databse
        in the server state directory if a name is provided. Otherwise it is stored in memory.
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

    def _set_update_time(self) -> str:
        """Set the ChecmDB update time to now
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
        """Return the ChemDB update time as a string
        Return 'never' if the databse is empty.
        """
        s = self._sess
        tt = s.query(TimeUpdate).first()
        if tt is None:
            return 'never'
        else:
            return timelib.datetime_to_str(tt.dt, in_local_tz=True)

    def get_db_stats(self) -> dict:
        """Return the number of each kind of records we have."""
        s = self._sess
        rdct = {}
        for idname, classname in ChemStockDB._ITM_LIST:
            rdct[idname] = s.query(classname).count()
        return rdct

    def update_from_QAI(self) -> bool:
        """Attempt to update the local ChemStock using the qaisession.
        """
        qaisession = self.qaisession
        if qaisession is None or not qaisession.is_logged_in():
            return False
        # get the locally stored timestamp data from our database
        cur_tsdata = self.load_TS_data()
        newds = qai_helper.QAIDataset(None, cur_tsdata)
        # load those parts from QAI that are out of date
        update_dct = qaisession.clever_update_QAI_dump(newds)
        update_ok = self.loadQAI_data(newds, update_dct)
        return update_ok

    def loadQAI_data(self,
                     qaiDS: qai_helper.QAIDataset,
                     update_dct: typing.Optional[qai_helper.QAIUpdatedct]=None) -> bool:
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
            do_update = upd_dct.get(idname, True)
            if do_update:
                # first, empty the table, then reload from scratch
                s.query(classname).delete()
                s.commit()
                for r_dct in qaidct[idname]:
                    # print("BLA {}".format(r_dct))
                    s.add(classname(**r_dct))
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
        We return the nominal state record and to booleans:
        ismissing, hasexpired.

        Strategy: we assign values to the various possible states and sort according
        to these values.
        any missing record will be the first one.
        the exp record is the last one (should exist, check the date with current date)
        the nominal state is the second to last in the list.
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
            odct = dict(MISSING=-1, MADE=0, VALIDATED=1, IN_USE=2, USED_UP=5, EXPIRED=6)
            try:
                slst.sort(key=lambda a: odct[a['status']])
            except KeyError:
                raise RuntimeError("status field missing in state record {}".format(slst))
            exp_dict = slst[-1]
            nom_state = slst[-2]
            ismissing = slst[0]['status'] == 'MISSING'
        # we could have no expired record, but a used up record instead.
        if exp_dict['status'] == 'EXPIRED':
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

    def generate_webclient_stocklist(self) -> dict:
        """Generate the stock list in a form required by the web client
        the dict returned has the following entries:
        loclst: a list of dicts containing the stock locations, e.g.
            [{'id': 10000, 'name': 'SPH'}, {'id': 10001, 'name': 'SPH\\638'}, ... ]

        the itemlst is a list of dicts containing:
        {'id': 18478, 'last_seen': None, 'lot_num': '2019AD3EB',
           'notes': '8 bottles of spare reagents',
           'qcs_location_id': 10010,
           'qcs_reag_id': 6297, 'rfid': 'REPLACE ME'},
        {'id': 18479, 'last_seen': None, 'lot_num': 'INT.BP.17.02',
           'notes': None, 'qcs_location_id': 10016,
           'qcs_reag_id': 6217, 'rfid': 'REPLACE ME'}

        the itmstatlst is a list of dicts containing:
        {'id': 41418, 'occurred': '2021-04-30T07:00:00Z',
           'qcs_reag_item_id': 18512, 'qcs_user_id': 113, 'status': 'EXPIRED'},
        {'id': 41419, 'occurred': '2018-06-01T22:54:26Z',
           'qcs_reag_item_id': 18513, 'qcs_user_id': 112, 'status': 'MADE'},
        {'id': 41420, 'occurred': '2020-04-03T00:00:00Z',
           'qcs_reag_item_id': 18513, 'qcs_user_id': 112, 'status': 'EXPIRED'}

        the reagentlst is a list of dicts containing:
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
        loclst = [dict(row) for row in self._sess.execute(Location.__table__.select())]
        itmlst = [dict(row) for row in self._sess.execute(Reagent_Item.__table__.select())]
        itmstat = [dict(row) for row in self._sess.execute(Reagent_Item_Status.__table__.select())]

        # create a Dict[locationid, List[reagentitem]] and a Dict[RFID, reagentitem]
        dd = {}
        # rfid_reagitem_dct = ff = {}
        ff = {}
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
        locid_reagitem_dct = rr = {}
        for location in loclst:
            loc_id = location.get('id', None)
            rr[loc_id] = (location, dd.get(loc_id, []))
        assert len(rr) == len(loclst), "problem with location ids!"
        #
        # collect the state records for each reagent item...
        zz = {}
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
            state_info = self.calc_final_state(state_lst) if state_lst is not None else None
            ritemdct[reag_item_id] = (reag_item, state_info)
        # create a Dict[reagentid, reagent]
        rl = [dict(row) for row in self._sess.execute(Reagent.__table__.select())]
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
        return {"loclst": loclst, "locdct": locid_reagitem_dct}
    # "ritemdct": ritemdct, "rfiddct": rfid_reagitem_dct}
    # "reagentdct": rg,
