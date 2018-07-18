
# A module to manage a local copy of the reagent database using sqlite3 and sqlalchemy

import typing
import logging

import sqlalchemy as sql
import sqlalchemy.orm as orm
from sqlalchemy.ext.declarative import declarative_base

# import serverlib.timelib as timelib
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


# for each table above, keep a time of when it was last updated on the QAI server.
class TableChange(Base):
    __tablename__ = 'tabchange'
    table_name = sql.Column(sql.String, primary_key=True)
    stamp = sql.Column(sql.String)


class ChemStockDB:
    def __init__(self,
                 locQAIfname: typing.Optional[str]) -> None:
        """
        This stock information is stored to a local file locQAIfname as an sqlite3 databse
        in the server state directory if a name is provided. Otherwise it is stored in memory.
        """
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

    def loadQAI_data(self, qaiDS: qai_helper.QAIDataset) -> bool:
        """Replace the database contents with the data contained in qaidct.
        Return := 'the update was successful'
        """
        s = self._sess
        # first, add the data....
        qaidct = qaiDS.get_data()
        for idname, classname in [(qai_helper.QAISession.QAIDCT_LOCATIONS, Location),
                                  (qai_helper.QAISession.QAIDCT_USERS, User),
                                  (qai_helper.QAISession.QAIDCT_REAITEM_COMPOSITION, Reagent_Item_Composition),
                                  (qai_helper.QAISession.QAIDCT_REAGENTS, Reagent),
                                  (qai_helper.QAISession.QAIDCT_REAGENT_ITEMS, Reagent_Item),
                                  (qai_helper.QAISession.QAIDCT_REAITEM_STATUS, Reagent_Item_Status)]:
            for r_dct in qaidct[idname]:
                # print("BLA {}".format(r_dct))
                s.add(classname(**r_dct))
            s.commit()
        # now add the timestamps
        tsdct = qaiDS.get_timestamp()
        for k, val in tsdct.items():
            tdct = dict(table_name=k, stamp=val)
            s.add(TableChange(**tdct))
        s.commit()
        return True

    def load_TS_data(self) -> qai_helper.QAIChangedct:
        """Retrieve the current timestamp data from the database."""
        rdct: qai_helper.QAIChangedct = {}
        for tc in self._sess.query(TableChange):
            rdct[tc.table_name] = tc.stamp
        return rdct
