
import py.path
# import pytest

import serverlib.QAILib as QAILib


qai_url = "https://qai.cfenet.ubc.ca:3000/qcs_reagents/json_get"
rubbish_url = "https://bla.bla.com"


class Test_qailib:

    def test_rawgetit_01(self):
        res = QAILib.raw_get_json_data(qai_url)
        print("GOOOT {}".format(res))
        assert res is not None, "failed to get reagents data"

    def test_getit_02(self):
        res = QAILib.get_json_data_with_time(qai_url)
        if not isinstance(res, dict):
            raise RuntimeError("Expected a dict")
        print("GOOOT {}".format(res))
        assert res is not None, "failed to get reagents data"

    def test_get_bla(self):
        res = QAILib.get_json_data_with_time(rubbish_url)
        if res is not None:
            raise RuntimeError("Expected None")

    def BLAtest_qai_01(self, tmpdir: py.path.local):
        print("TMPDIR IS '{}".format(tmpdir))
        locfname = tmpdir.join('./bla.yaml')
        qai = QAILib.QAIdata(qai_url, locfname)
        # assert False, "force fail"
