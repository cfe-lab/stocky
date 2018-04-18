
import py.path
import pytest
import os.path

import serverlib.QAILib as QAILib
import serverlib.yamlutil as yamlutil


qai_url = "https://qai.cfenet.ubc.ca:3000/qcs_reagents/json_get"
rubbish_url = "https://bla.bla.com"


def get_testfilename(fn: str) -> str:
    abspath = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(abspath, 'qailib-testfiles', fn)


RAW_TESTDATA_FILE01 = get_testfilename('rawdata-2018-04-16.json')


class Test_qailib:
    @pytest.mark.skip(reason="skip QAI test for now")
    def test_rawgetit_01(self) -> None:
        res = QAILib.raw_get_json_data(qai_url)
        print("GOOOT {}".format(res))
        assert res is not None, "failed to get reagents data"

    @pytest.mark.skip(reason="skip QAI test for now")
    def test_getit_02(self) -> None:
        res = QAILib.get_json_data_with_time(qai_url)
        if not isinstance(res, dict):
            raise RuntimeError("Expected a dict")
        print("GOOOT {}".format(res))
        assert res is not None, "failed to get reagents data"

    def test_get_bla(self):
        "Accessing a nonexistent URL should raise an exception"""
        res = QAILib.get_json_data_with_time(rubbish_url)
        if res is not None:
            raise RuntimeError("Expected None")

    def test_splitlocstr(self):
        """Test behaviour of s plitting of location strings."""
        test_lst = [('515 /604/605 /669/ 638/ 525A',
                     ['515', '604', '605', '669', '638', '525A']),
                    ('605 ACIDS BIN', ['605 ACIDS BIN']),
                    ('605; 669 TC', ['605', '669 TC'])]
        for locstr, exp_res in test_lst:
            got_res = QAILib.BaseQAIdata.splitlocstring(locstr)
            assert got_res == exp_res, "unexpected result!"

    def test_qai_01(self, tmpdir: py.path.local) -> None:
        """A QAIdata struct without data should behave sensibly"""
        locfname = str(tmpdir.join('bla.yaml'))
        qai = QAILib.QAIdata(qai_url, locfname)
        has_data = qai.has_qai_data()
        print("hasdata: '{}'".format(has_data))
        dt = qai.get_qai_downloadtimeUTC()
        print("datetime: '{}'".format(dt))
        # should not have data at this point
        if has_data or dt is not None:
            raise RuntimeError("hasdata and datetime should be None!")
        # trying to dump data to file should raise an error
        with pytest.raises(RuntimeError):
            qai.dumpfileQAIdata()

    def test_qai_02(self, tmpdir: py.path.local) -> None:
        """A QAIdata struct with data should be able to dump data and read it back"""
        locfname = str(tmpdir.join('/bla.yaml'))
        qai = QAILib.QAIdata(qai_url, locfname)
        has_downloaded = qai._loadrawdata(RAW_TESTDATA_FILE01)
        print("loading raw data from file...returned {}".format(has_downloaded))
        has_data = qai.has_qai_data()
        print("hasdata: '{}'".format(has_data))
        if not (has_data and has_downloaded):
            raise RuntimeError('failed to load raw data')
        dt = qai.get_qai_downloadtimeUTC()
        print("datetime: '{}'".format(dt))
        if dt is None:
            raise RuntimeError("hasdata and no datetime found!")
        loc_dct = qai._check_massaga_data()
        print("did_massage: '{}'".format(loc_dct is not None))
        loc_summary = qai._location_summary()
        if loc_summary is None:
            raise RuntimeError("loc_summary is None!")
        # print(" \n".join(["%30s : %d" % t for t in loc_summary]))

        # now dump the file, read it back and verify correctness
        qai.dumpfileQAIdata()
        retval = yamlutil.readyamlfile(locfname)
        assert retval is not None, "failed to read dumped file"
        assert retval == qai.cur_data, "dumped data is not equal"

        # now call generate_webclient_stocklist(self)
        ret_dct = qai.generate_webclient_stocklist()
        assert isinstance(ret_dct, dict), "expected dict"

        # assert False, "force fail"
