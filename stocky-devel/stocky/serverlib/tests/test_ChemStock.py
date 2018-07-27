
# import typing
import pytest

import serverlib.yamlutil as yamlutil
import serverlib.qai_helper as qai_helper


import serverlib.ChemStock as ChemStock


withchemstock = pytest.mark.skipif(not pytest.config.option.with_chemstock,
                                   reason="needs --with_chemstock option in order to run")

csdb = None


def setup_module():
    qaids = yamlutil.readyamlfile("./qaidump.yaml")
    locdbname = "bli.sqlite"
    locdbname = None
    global csdb
    csdb = ChemStock.ChemStockDB(locdbname)
    retval = csdb.loadQAI_data(qaids)
    assert isinstance(retval, bool), "bool expected"
    assert retval, "loadQAIdata failed"


@withchemstock
class Test_Chemstock:

    @classmethod
    def setup_class(cls) -> None:
        # qaidct = yamlutil.readyamlfile("./qaidump.yaml")
        # cls.locdbname = "bli.sqlite"
        # cls.locdbname = None
        # cls.csdb = ChemStock.ChemStockDB(qaidct, cls.locdbname)
        # print("DB NAME: {}".format(cls.csdb._locQAIfname))
        # assert False, "force fail"
        cls.csdb = csdb

    def test_setupDB(self):
        pass

    def test_loadTS01(self):
        tsdct = self.csdb.load_TS_data()
        print("BLA {}".format(tsdct))
        assert isinstance(tsdct, dict), "dict expected"
        assert set(tsdct.keys()) == qai_helper.QAISession.qai_key_set, "unexpted dict keys"
        # assert False, " force fail"

    def test_generate_webclient_stocklist01(self):
        lverb = True
        rdct = self.csdb.generate_webclient_stocklist()
        assert isinstance(rdct, dict), "dict expected"
        if lverb:
            print("rdct {}".format(rdct))
        loclst = rdct["loclst"]
        assert isinstance(loclst, list), "list expected"
        
        assert False, " force fail"
