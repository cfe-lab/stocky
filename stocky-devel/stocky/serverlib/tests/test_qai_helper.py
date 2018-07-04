
import py.path
import pytest
import os.path

import requests
import serverlib.qai_helper as qai_helper
# import serverlib.yamlutil as yamlutil

# this is James Nakagawa's test server
qai_url = "http://192.168.69.170:4567"

auth_uname = 'wscott'
auth_password = 'abc123'

# qai_url = "https://qai.cfenet.ubc.ca:3000/qcs_reagents/json_get"
# rubbish_url = "https://bla.bla.com"


def get_testfilename(fn: str) -> str:
    abspath = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(abspath, 'qailib-testfiles', fn)


RAW_TESTDATA_FILE01 = get_testfilename('rawdata-2018-04-16.json')


def check_dct_type(tdct: dict, totest: dict):
    """Test whether the totest items are of the type specified in tdct."""
    assert isinstance(totest, dict), 'dict expected'
    exp_keys = set(tdct.keys())
    got_keys = set(totest.keys())
    assert exp_keys == got_keys, "unequal keys"
    for k, v in totest.items():
        exp_type = tdct[k]
        if not isinstance(v, exp_type):
            raise RuntimeError("{}: {} entry: expected {}, but got {}".format(k,
                                                                              v,
                                                                              exp_type,
                                                                              type(v)))


class Test_qai_helper:

    def setup_method(self) -> None:
        self.s = qai_helper.Session()
        self.s.login(qai_url, auth_uname, auth_password)

    def test_wrong_login01(self) -> None:
        """Logging in to the correct host with a wrong password should raises an expection."""
        with pytest.raises(RuntimeError):
            self.s.login(qai_url, auth_uname, 'blapassword')

    def test_wrong_login02(self) -> None:
        "Logging in to a wrong host should raise an exception."""
        with pytest.raises(requests.exceptions.ConnectionError):
            self.s.login("http://localhost", auth_uname, 'blapassword')

    def test_illegalurl01(self):
        """An illegal URL should raise an exception"""
        # NOTE: we have omitted the leading backslash
        with pytest.raises(requests.exceptions.InvalidURL):
            self.s.get_json('qcs_location/list')

    def test_get_location_list(self):
        rjson = self.s.get_json('/qcs_location/list')
        assert isinstance(rjson, list), 'list expected'
        tdct = {'id': int, 'name': str}
        for d in rjson:
            check_dct_type(tdct, d)

    def test_get_reagent_list(self):
        """Getting the reagent list should succeed and provide
        the expected data structure."""
        lverb = True
        rjson = self.s.get_json('/qcs_reagent/list')
        if not isinstance(rjson, dict):
            print("expected a dict, but got {}".format(type(rjson)))
            print("data {}".format(rjson))
            assert False, "force fail"
        if lverb:
            print("got data {}".format(rjson))
        exp_keys = set(['items', 'total_count'])
        if set(rjson.keys()) != exp_keys:
            assert False, "unexpected keys {}".format(rjson.keys())
        if lverb:
            print("keys: {}".format(rjson.keys()))
        # check items entry
        itemlst = rjson['items']
        assert isinstance(itemlst, list), "items entry must be a list"
        tdct = {'id': int, 'name': str}
        for d in itemlst:
            check_dct_type(tdct, d)
        # check total_count entry
        tot_count = rjson['total_count']
        assert isinstance(tot_count, int), "integer expected"
        # assert False, "force fail"

    def test_location_items(self):
        lverb = True
        loclst = self.s.get_json('/qcs_location/list')
        reagentlst = self.s.get_json('/qcs_reagent/list')
        loc_id = loclst[0]['id']
        query_dct = {'id': loc_id}
        if lverb:
            print("search for locid {}".format(loc_id))
        rlst = self.s.get_json('/qcs_reagent/location_items', params=query_dct)
        print("goot {}".format(rlst))
        assert False, "force fail"

        
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

    @pytest.mark.skip(reason="skip QAI test for now")
    def test_get_bla(self):
        "Accessing a nonexistent URL should raise an exception"""
        res = QAILib.get_json_data_with_time(rubbish_url)
        if res is not None:
            raise RuntimeError("Expected None")
