
import typing

import serverlib.yamlutil as yamlutil
import serverlib.qai_helper as qai_helper


import serverlib.ChemStock as ChemStock


class Test_Chemstock:

    @classmethod
    def setup_class(cls) -> None:
        qaidct = yamlutil.readyamlfile("./qaidump.yaml")
        cls.locdbname = "bli.sqlite"
        cls.locdbname = None
        cls.csdb = ChemStock.ChemStockDB(qaidct, cls.locdbname)

        print("DB NAME: {}".format(cls.csdb._locQAIfname))
        # assert False, "force fail"

    def test_dummy01(self):
        pass
