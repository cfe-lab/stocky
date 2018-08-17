
# import typing
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

# csdb = None


def OLD_setup_module():
    qaids = yamlutil.readyamlfile("./qaidump.yaml")
    locdbname = "bli.sqlite"
    locdbname = None
    global csdb
    csdb = ChemStock.ChemStockDB(locdbname, None)
    retval = csdb.loadQAI_data(qaids)
    assert isinstance(retval, bool), "bool expected"
    assert retval, "loadQAIdata failed"


class commontests:

    def test_loadTS01(self):
        tsdct = self.csdb.load_TS_data()
        print("BLA {}".format(tsdct))
        assert isinstance(tsdct, dict), "dict expected"
        assert set(tsdct.keys()) == qai_helper.QAISession.qai_key_set, "unexpted dict keys"
        # assert False, " force fail"

    @pytest.mark.skip(reason="method is in flusx")
    def test_generate_webclient_stocklist01(self):
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
        """get DB stats"""
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


@withchemstock
class Test_Chemstock_NOQAI(commontests):
    """tests in which we load some data froma YAML file."""

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
        """As we don't have access to QAI, this should return False."""
        retval = self.csdb.update_from_QAI()
        assert isinstance(retval, bool), "bool expected"
        assert not retval, "False expected"


@withchemstockANDqa1
class Test_Chemstock_WITHQAI(commontests):
    """Tests with chemstock and with QAI access"""

    @classmethod
    def setup_class(cls) -> None:
        # first, set up a QAIsession and log in
        cls.qaisession = sess = qai_helper.QAISession(test_qai_helper.TESTqai_url)
        sess.login(test_qai_helper.TESTauth_uname,
                   test_qai_helper.TESTauth_password)

        # cls.locdbname = "bli.sqlite"
        cls.locdbname = None
        cls.csdb = ChemStock.ChemStockDB(cls.locdbname, sess, 'America/Vancouver')
        print("DB NAME: {}".format(cls.csdb._locQAIfname))
        # assert False, "force fail"

    def test01(self):
        # assert False, "force fail!"
        pass

    def test_update_from_qai02(self):
        """Actually update our local DB from QAI over the network.."""
        lverb = True
        csdb = self.csdb
        old_upd = csdb.get_update_time()
        assert isinstance(old_upd, str), "string expected"
        if lverb:
            print("OLD UPDATE {}".format(old_upd))
        retval = csdb.update_from_QAI()
        assert isinstance(retval, bool), "bool expected"
        assert retval, "QAI update failed !"

        new_upd = csdb.get_update_time()
        assert isinstance(new_upd, str), "string expected"
        if lverb:
            print("NEW UPDATE {}".format(new_upd))
        assert old_upd != new_upd, "UPDATE TIME MATCH!"
        # assert False, "force fail"
