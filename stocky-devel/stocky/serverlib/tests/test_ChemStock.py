""" Test the ChemStock module
"""

import pytest
import time

import serverlib.yamlutil as yamlutil
import serverlib.qai_helper as qai_helper


import serverlib.ChemStock as ChemStock

import serverlib.tests.test_qai_helper as test_qai_helper

withchemstock = pytest.mark.skipif(not pytest.config.option.with_chemstock,
                                   reason="needs --with_chemstock option in order to run")

withchemstockANDqa1 = pytest.mark.skipif(not pytest.config.option.with_cs_qai,
                                         reason="needs --with_cs_qai option in order to run")


class Test_funcs:
    """Test a number of helper functions in the ChemStock module,
    These functions do not depend on ChemStockDB
    """
    def test_sortloclist01(self) -> None:
        """ChemStock.sortloclist should preserve list length
        """
        olst = [{'name': r'SPH\West wing'},
                {'name': r'SPH\West wing\dog house'},
                {'name': r'SPH\East Wing'},
                {'name': r'SPH\West wing\cat house'},
                {'name': r'SPH'},
                {'name': r'SPH\East Wing\Aviary'}]

        sortlst = ChemStock.sortloclist(olst)
        print("GOOT {}".format(sortlst))
        # assert False, "force fail"
        # NOTE: this is not really checking for correct sorting..
        assert len(olst) == len(sortlst), "wrong list length"

    def test_hash01(self) -> None:
        """ChemStock.do_hash must produce the same hash irrespective of the order
        in which dict elements were added to a dict.
        """
        dohash = ChemStock.do_hash
        # create two identical dicts in different ways. The hash should be the same.
        adct = dict(a=3, b=2, c=1)
        bdct = {}
        for k, v in sorted(adct.items(), key=lambda a: a[1]):
            bdct[k] = v
        ahash = dohash(adct)
        bhash = dohash(bdct)
        assert ahash == bhash, "hashes are different"

    def test_retrieve_column_names(self) -> None:
        """Must be able to determine the column names of an SQL table."""
        # for idname, classname in ChemStockDB._ITM_LIST:
        classname = ChemStock.Reagent
        klst = classname.__table__.columns.keys()
        print("keylst {}".format(klst))
        assert isinstance(klst, list), "list expected"


class commontests:

    def test_loadTS01(self):
        """Loading database timestamp data must succeed and contain data
        for all tables defined."""
        tsdct = self.csdb.load_TS_data()
        print("BLA {}".format(tsdct))
        assert isinstance(tsdct, dict), "dict expected"
        assert set(tsdct.keys()) == qai_helper.QAISession.qai_key_set, "unexpted dict keys"
        # assert False, " force fail"

    def test_generate_webclient_stocklist01(self):
        """ generate_webclient_stocklist must return a dict with
        the required entries."""
        lverb = False
        rdct = self.csdb.generate_webclient_stocklist()
        assert isinstance(rdct, dict), "dict expected"
        if lverb:
            print("rdct {}".format(rdct))
        for k in ['loclst']:
            # , 'itmstatlst']:
            val = rdct["loclst"]
            assert isinstance(val, list), "list expected"
        for k in ['locdct', 'reagentdct']:
            val = rdct[k]
            assert isinstance(val, dict), "dict expected"
        # assert False, " force fail"

    def test_get_stats(self):
        """get_db_stats() must succeed and return a dict with required keys."""
        lverb = True
        rdct = self.csdb.get_db_stats()
        assert isinstance(rdct, dict), "dict expected"
        if lverb:
            print("rdct {}".format(rdct))
        assert set(rdct.keys()) == qai_helper.QAISession.qai_key_set, "unexpted dict keys"
        # assert False, " force fail"


class Test_Chemstock_EMPTYDB(commontests):
    """Tests that require an empty DB AND no qai ACCESS"""
    @classmethod
    def setup_class(cls) -> None:
        locdbname = None
        cls.csdb = ChemStock.ChemStockDB(locdbname, None, 'America/Vancouver')

    def test_time_update01(self):
        """get_update_time and set_update_time must work as expected
        """
        lverb = True
        upd_str = self.csdb.get_update_time()
        assert isinstance(upd_str, str), "string expected"
        if lverb:
            print("UPD 1 {}".format(upd_str))
        if upd_str != 'never':
            raise RuntimeError("expected 'never', got {}".format(upd_str))
        # now try to set the update time...
        upd_str = self.csdb._set_update_time()
        assert isinstance(upd_str, str), "string expected"
        if lverb:
            print("UPD 2 {}".format(upd_str))
        updalt_str = self.csdb.get_update_time()
        assert upd_str == updalt_str, "strings should be equal"
        # now try to update a bit later and check for change...
        time.sleep(1)
        new_upd = self.csdb._set_update_time()
        if lverb:
            print("UPD 3 {}".format(new_upd))
        assert upd_str != new_upd, "updates must be different!"
        # assert False, " force fail"

    def test_addlocchanges01(self) -> None:
        """Calling add_loc_changes with invalid location change data
        must raise a ValueError exception. The database must not be modified
        if a ValueError exception is raised.
        """
        csdb = self.csdb
        # reset should remove all records
        csdb.reset_loc_changes()
        ngot = csdb.number_of_loc_changes()
        assert isinstance(ngot, int), "int expected"
        assert ngot == 0, "n should be zero!"

        # a) location id is not an integer.
        wrong_locid = '99'
        locdat = [(1, 'missing'), (2, 'found'), (3, 'missing')]
        with pytest.raises(ValueError):
            csdb.add_loc_changes(wrong_locid, locdat)
        ngot = csdb.number_of_loc_changes()
        assert isinstance(ngot, int), "int expected"
        assert ngot == 0, "n should be zero!"

        # b) reagent item ids (1,2,3) are not all integers.
        wronglocdat = [(1, 'missing'), ('2', 'found'), ('3', 'missing')]
        with pytest.raises(ValueError):
            csdb.add_loc_changes(99, wronglocdat)
        ngot = csdb.number_of_loc_changes()
        assert isinstance(ngot, int), "int expected"
        assert ngot == 0, "n should be zero!"

        # c) opstrings are not strings
        wronglocdat = [(1, 'missing'), (2, 1001), (3, 'missing')]
        with pytest.raises(ValueError):
            csdb.add_loc_changes(99, wronglocdat)
        ngot = csdb.number_of_loc_changes()
        assert isinstance(ngot, int), "int expected"
        assert ngot == 0, "n should be zero!"

    def test_set_ignore_flag01(self) -> None:
        """Calling set_ignore_flag with wrong parameter types must raise a ValueError"""
        csdb = self.csdb
        with pytest.raises(ValueError):
            csdb.set_ignore_flag('100', True)
        with pytest.raises(ValueError):
            csdb.set_ignore_flag(100, 'False')

    def test_addlocchanges02(self) -> None:
        """Adding a reagent item location change must work as expected."""
        csdb = self.csdb
        locid = 99
        # reset should remove all records
        csdb.reset_loc_changes()
        ngot = csdb.number_of_loc_changes()
        assert isinstance(ngot, int), "int expected"
        assert ngot == 0, "n should be zero!"
        # add three changes
        locdat = [(1, 'missing'), (2, 'found'), (3, 'missing')]
        csdb.add_loc_changes(locid, locdat)
        ngot = csdb.number_of_loc_changes()
        assert ngot == 3, "expected three!"
        # read them back and check the contents
        hashcode, retdct = csdb.get_loc_changes(None)
        assert isinstance(retdct, dict), "dict expected"
        assert len(retdct.keys()) == 1, "single key expected in dict"
        rlst = retdct[locid]
        assert len(rlst) == 3, "list len of three expected"
        for reag_item_id, opstring, ignore, created_at in rlst:
            assert isinstance(reag_item_id, int), "int expected"
            assert isinstance(opstring, str), "string expected"
            assert isinstance(ignore, bool), "bool expected"
            assert not ignore, "ignore == False expected"
            assert isinstance(created_at, str), "string expected"
        # --
        # adding the same records again -- expect no change..
        csdb.add_loc_changes(locid, locdat)
        ngot = csdb.number_of_loc_changes()
        assert ngot == 3, "expected three!"
        # read back the data (check that created_at entries was not changed
        # by previous add_loc_changes)
        newhashcode, newretdct = csdb.get_loc_changes(None)
        assert isinstance(newretdct, dict), "dict expected"
        assert len(newretdct.keys()) == 1, "single key expected in dict"
        assert hashcode == newhashcode, "unexpected hash code!"
        assert retdct == newretdct, "expected the same dict!"

        # change the ignore flag of an existing locmutation record
        test_reag_item = 1
        stat_dct = csdb.set_ignore_flag(test_reag_item, True)
        assert isinstance(stat_dct, dict), "dict expected"
        assert stat_dct["ok"], " stat_dct ok == True expected"
        # should have same number of records, but a different hash...
        ngot = csdb.number_of_loc_changes()
        assert ngot == 3, "expected three!"
        newhashcode, newretdct = csdb.get_loc_changes(None)
        assert isinstance(newretdct, dict), "dict expected"
        assert len(newretdct.keys()) == 1, "single key expected in dict"
        assert hashcode != newhashcode, "unexpected hash code!"
        assert retdct != newretdct, "expected a different dict!"
        # now make sure the ignore flag was actually set
        for reag_item_id, opstring, ignore, created_at in newretdct[locid]:
            my_cond = (reag_item_id == test_reag_item) ^ (not ignore)
            assert my_cond, "unexpected ignore flag {}: {}".format(reag_item_id, ignore)

        # add a different loc change opstring...
        locdat = [(test_reag_item, 'found'), (2, 'found'), (3, 'missing')]
        csdb.add_loc_changes(locid, locdat)
        ngot = csdb.number_of_loc_changes()
        assert ngot == 3, "expected three!"
        # read back all changes
        hashkey, dct = csdb.get_loc_changes()
        assert isinstance(dct, dict), "dict expected"
        assert isinstance(hashkey, str), "string expected"
        # changing the opstring should also have reset the do_ignore flag to False.
        for reag_item_id, opstring, ignore, created_at in dct[locid]:
            assert not ignore, "ignore == False expected"
        # print("dd {}".format(dct))
        # attempt to set the ignore flag of an non-existant locmutation
        stat_dct = csdb.set_ignore_flag(test_reag_item+100, True)
        assert isinstance(stat_dct, dict), "dict expected"
        assert not stat_dct["ok"], " stat_dct ok == False expected"

        # next, pass the hash back in.. we should get a None for dct indicating 'no changes'
        oldhashkey = hashkey
        hashkey, none_dct = csdb.get_loc_changes(oldhashkey)
        assert isinstance(hashkey, str), "string expected"
        assert hashkey == oldhashkey, "old hash expected"
        assert none_dct is None, "expected None for dct"
        gotlst = dct[locid]
        assert len(gotlst) == len(locdat), "unexpected length"
        print("locc {}".format(gotlst))
        # assert False, "force fail"
        # remove all records to finish up
        csdb.reset_loc_changes()


@withchemstock
class Test_Chemstock_NOQAI(commontests):
    """Tests in which we load some data from a YAML file."""

    @classmethod
    def setup_class(cls) -> None:
        # cls.locdbname = "bli.sqlite"
        cls.locdbname = None
        cls.csdb = ChemStock.ChemStockDB(cls.locdbname, None, 'America/Vancouver')
        print("DB NAME: {}".format(cls.csdb._locQAIfname))
        print("loading data from YAML file...")
        qaids = yamlutil.readyamlfile("./qaidump.yaml")
        load_ok = cls.csdb.loadQAI_data(qaids)
        assert load_ok, "data load failed"
        # assert False, "force fail"

    def test_update_from_qai01(self):
        """ haschanged should be False after calling update_from_QAI
        without access to QAI"""
        self.csdb.update_from_QAI()
        haschanged = self.csdb._haschanged
        assert isinstance(haschanged, bool), "bool expected"
        assert not haschanged, "False expected"


@withchemstockANDqa1
class Test_Chemstock_WITHQAI(commontests):
    """Tests with chemstock and with QAI access"""

    @classmethod
    def setup_class(cls) -> None:
        # first, set up a QAIsession and log in
        cls.qaisession = sess = qai_helper.QAISession(test_qai_helper.TESTqai_url)
        resdct = sess.login_try(test_qai_helper.TESTauth_uname,
                                test_qai_helper.TESTauth_password)
        login_ok = resdct.get('ok', False)
        if not login_ok:
            print("**** QAI login failed ****")
        # cls.locdbname = "bli.sqlite"
        cls.locdbname = None
        cls.csdb = ChemStock.ChemStockDB(cls.locdbname, sess, 'America/Vancouver')
        print("DB NAME: {}".format(cls.csdb._locQAIfname))
        # assert False, "force fail"

    def test_update_from_qai02(self):
        """Update our local DB from QAI over the network with net access."""
        lverb = True
        csdb = self.csdb
        old_upd = csdb.get_update_time()
        assert isinstance(old_upd, str), "string expected"
        if lverb:
            print("OLD UPDATE {}".format(old_upd))
        csdb.update_from_QAI()

        new_upd = csdb.get_update_time()
        assert isinstance(new_upd, str), "string expected"
        if lverb:
            print("NEW UPDATE {}".format(new_upd))
        assert old_upd != new_upd, "UPDATE TIME MATCH!"
        # assert False, "force fail"
