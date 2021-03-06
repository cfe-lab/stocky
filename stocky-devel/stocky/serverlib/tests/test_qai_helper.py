"""Test the qai_helper module"""
# import py.path
import typing
import pytest
import os.path
import random
import string


import requests
import serverlib.qai_helper as qai_helper
import serverlib.yamlutil as yamlutil

# this is 200
HTTP_OK = qai_helper.HTTP_OK
# this is 201
HTTP_CREATED = qai_helper.HTTP_CREATED

# this 500
HTTP_INTERNAL_SERVER_ERROR = qai_helper.HTTP_INTERNAL_SERVER_ERROR

# this is 422
HTTP_UNPROCESSABLE = qai_helper.HTTP_UNPROCESSABLE


# withqai = pytest.mark.skipif(not pytest.config.option.with_qai,
#                             reason="needs --with_qai option in order to run")
withqai = pytest.mark.skipif(not pytest.config.getoption("with_qai"),
                             reason="needs --with_qai option in order to run")

dumpchemstock = pytest.mark.skipif(not pytest.config.option.dump_chemstock,
                                   reason="needs --dump_chemstock and --with_qai option in order to run")

QAI_DUMP_FILE = "./qaidump.yaml"

# this is James Nakagawa's test server
# TESTqai_url = "http://192.168.69.170:4567"
# TESTqai_url = "http://192.168.93.190:4567"

# this is Jame's pre-release test server
TESTqai_url = "http://192.168.69.223:8000"

TESTauth_uname = 'stocky_test'
TESTauth_password = 'abc123'

# qai_url = "https://qai.cfenet.ubc.ca:3000/qcs_reagents/json_get"
# rubbish_url = "https://bla.bla.com"


# this reagent is expected to be in the database
TEST_REAGENT_NAME = 'test reagent'

PATH_LOCATION_LIST = qai_helper.PATH_LOCATION_LIST
PATH_REAGENT_RECEIVE = qai_helper.PATH_REAGENT_RECEIVE
PATH_REAGENT_LIST_REAGENTS = qai_helper.PATH_REAGENT_LIST_REAGENTS
PATH_REAGENT_LIST = qai_helper.PATH_REAGENT_LIST
PATH_REAGENT_LOCITEMS = qai_helper.PATH_REAGENT_LOCITEMS
PATH_REAGENT_SHOW = qai_helper.PATH_REAGENT_SHOW
PATH_REAGITEM_STATUS = qai_helper.PATH_REAGITEM_STATUS
PATH_REAGENT_VERIFY_LOCATION = qai_helper.PATH_REAGENT_VERIFY_LOCATION
PATH_REAGITEM_LIST = qai_helper.PATH_REAGITEM_LIST
PATH_REAGENT_LIST_SUPPLIERS = qai_helper.PATH_REAGENT_LIST_SUPPLIERS

PATH_USER_LIST = qai_helper.PATH_USER_LIST

# -- the following endpoints are used for creating reagents and reagent items for testing
# they are not part of the 'official' API that stocky would normally use.

TPATH_REAGENT_SAVE = '/qcs_reagent/save'
TPATH_REAGENT_ITEM = '/qcs_reagent/item'

# in order to be able to check whether our tests cover all of the
# published API in {setup, teardown}_module, we keep a set of all possible API calls.
api_set = frozenset([('get', PATH_LOCATION_LIST),
                     ('get', PATH_REAGITEM_LIST),
                     ('get', PATH_REAGENT_RECEIVE),
                     ('get', PATH_REAGENT_LIST_SUPPLIERS),
                     ('get', PATH_REAGENT_LIST_REAGENTS),
                     ('get', PATH_REAGENT_LIST),
                     ('get', PATH_REAGENT_LOCITEMS),
                     ('get', PATH_REAGENT_SHOW),
                     ('post', TPATH_REAGENT_ITEM),
                     ('patch', TPATH_REAGENT_ITEM),
                     ('post', TPATH_REAGENT_SAVE),
                     ('patch', TPATH_REAGENT_SAVE),
                     ('post', PATH_REAGITEM_STATUS),
                     ('delete', PATH_REAGITEM_STATUS),
                     ('patch', PATH_REAGENT_VERIFY_LOCATION)])


_callset: typing.Set[typing.Tuple[str, str]] = set()


class TrackerSession(qai_helper.QAISession):
    """A session that keeps track of all calls performed."""
    def __init__(self, qai_path: str) -> None:
        super().__init__(qai_path)
        self._callset: typing.Set[typing.Tuple[str, str]] = set()

    def patch_json(self, path: str, data: typing.Any, params=None, retries=3) -> qai_helper.RequestValue:
        _callset.add(('patch', path))
        return super().patch_json(path, data, params=params, retries=retries)

    def post_json(self, path: str, data: typing.Any, retries=3) -> qai_helper.RequestValue:
        _callset.add(('post', path))
        return super().post_json(path, data, retries=retries)

    def get_json(self, path: str, params: dict = None, retries: int = 3) -> qai_helper.RequestValue:
        _callset.add(('get', path))
        return super().get_json(path, params, retries=retries)

    def delete_json(self, path: str, params: dict = None, retries: int = 3) -> qai_helper.RequestValue:
        _callset.add(('delete', path))
        return super().delete_json(path, params, retries=retries)

    def generate_receive_url(self, locid: int, rfidlst: typing.List[str], newstock: bool) -> str:
        _callset.add(('get', PATH_REAGENT_RECEIVE))
        return super().generate_receive_url(locid, rfidlst, newstock)


class FaultySession(qai_helper.QAISession):
    """A session that always returns an HTTP error."""
    def __init__(self, qai_path: str) -> None:
        super().__init__(qai_path)

    def patch_json(self, path: str, data: typing.Any, params=None, retries=3) -> qai_helper.RequestValue:
        return [HTTP_OK+1, None]

    def post_json(self, path: str, data: typing.Any, retries=3) -> qai_helper.RequestValue:
        return [HTTP_OK+1, None]

    def get_json(self, path: str, params: dict = None, retries: int = 3) -> qai_helper.RequestValue:
        return [HTTP_OK+1, None]

    def delete_json(self, path: str, params: dict = None, retries: int = 3) -> qai_helper.RequestValue:
        return [HTTP_OK+1, None]

    def generate_receive_url(self, locid: int, rfidlst: typing.List[str], newstock: bool) -> str:
        return [HTTP_OK+1, None]

    def _rawget(self, path: str, params: dict = None, retries: int = 3) -> requests.Response:
        """Perform a get call to the server, in which we do NOT expect a json response
        from the server.
        """
        resp = requests.Response()
        resp.status_code = HTTP_OK + 1
        # rval = resp.text
        return resp


def setup_module(module) -> None:
    print("SEETUP MODULE")
    # assert False, "force fail"


def teardown_module(module) -> None:
    missing_api = api_set - _callset
    if missing_api:
        print("Missing calls:")
        print("\n".join(["{}".format(stup) for stup in missing_api]))
        # raise RuntimeError("Incomplete test of the API")


def get_testfilename(fn: str) -> str:
    abspath = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(abspath, 'qailib-testfiles', fn)


RAW_TESTDATA_FILE01 = get_testfilename('rawdata-2018-04-16.json')


def check_dct_type(tdct: dict, totest: dict) -> None:
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


class Test_qai_helpers:
    """These tests are independent of access to a QAI server."""

    def test_tojson01(self) -> None:
        """Encoding a dict with a complex key raises a TypeError"""
        s = {(1, 2): 'hello'}
        with pytest.raises(TypeError):
            qai_helper.tojson(s)

    def test_tojson02(self) -> None:
        """Encoding a user-defined class should work."""
        class bla:
            def __init__(self):
                self.bg = 'red'
                self.goo = 'blue'
        b = bla()
        rs = qai_helper.tojson(b)
        assert isinstance(rs, str), 'string expected'

    def test_jsonconvert(self) -> None:
        """Encode and decoding should produce the same data structure.
        NOTE: tuple are converted into lists in json -- therefore our tests
        should not use them.
        NOTE: complex numbers come back as strings -- do not test either.
        NOTE: sets cannot be used either.
        """
        a = dict(a=100.0, b=99, c='hello', d=[12, 'blu'])
        b = [100.0, -99, 'bla', ['sub', 'list']]
        c = [1, 2, 3]
        for var in [a, b, c]:
            transmit_bytes = qai_helper.tojson(var)
            got_var = qai_helper.fromjson(transmit_bytes)
            assert got_var == var, "variable is not the same "

    def test_safe_fromjson(self) -> None:
        """
        safe_fromjson should provide a data structure or None
        """
        avar = dict(a=100.0, b=99, c='hello', d=[12, 'blu'])
        astr = qai_helper.tojson(avar)
        bstr = "this is not json"
        for var, exp_res in [(astr, avar), (bstr, None)]:
            res = qai_helper.safe_fromjson(var)
            assert res == exp_res, "got unexpected result"

    def test_login_try_wrong_parameters(self) -> None:
        """Ensure that login_try behaves appropriately when
        passed nonsense arguments.
        These tests do not require access to the QAI server.
        """
        s = qai_helper.Session(TESTqai_url)
        for usr, passwd in [(None, 'password'),
                            ('user', None)]:
            res = s.login_try(usr, passwd)
            assert isinstance(res, dict), "dict expected"
            assert not res['ok'], "ok = False expected"

    def test_login_try_invalid_URL(self) -> None:
        for hname in ["", "192.abc", 145, "rss:bka:hello", "hello/%bla?goo"]:
            s = qai_helper.Session(hname)
            res = s.login_try('user', 'password')
            assert isinstance(res, dict), "dict expected"
            assert not res['ok'], "ok = False expected"
            print("GOT msg '{}'".format(res['msg']))
        # assert False, "force fail"

    def test_qaidataset(self) -> None:
        rdct: qai_helper.QAIdct = None
        tsdct: qai_helper.QAIChangedct = {}
        tsdct[qai_helper.QAISession.QAIDCT_REAGENTS] = 'now'
        ds = qai_helper.QAIDataset(rdct, tsdct)
        data_dct = ds.get_data()
        assert isinstance(data_dct, dict), "dict expected"
        ts_dct = ds.get_timestamp()
        assert ts_dct == tsdct, "unexpected dict"
        # assert False, "force fail"


@withqai
class Test_qai_log_in:
    """These tests are performed before a valid log in has been performed."""

    def setup_method(self) -> None:
        self.s = qai_helper.Session(TESTqai_url)

    def test_nologin(self):
        """Using the API without first logging in raises an exception"""
        with pytest.raises(RuntimeError):
            self.s.get_json(PATH_LOCATION_LIST)

    def test_wrong_login01(self) -> None:
        """Logging in to the correct host with a wrong password should
        raises an exception.
        NOTE: This test will only pass if the remote server is actually reachable.
        """
        # with pytest.raises(RuntimeError):
        try:
            self.s.login(TESTauth_uname, 'blapassword')
        except RuntimeError:
            # expected behaviour
            pass
        except requests.exceptions.ConnectionError:
            print("server is down, testing is not possible")
        except Exception:
            raise

    def test_wrong_login02(self) -> None:
        "Logging in to a wrong host should raise an exception."""
        ss = qai_helper.Session("http://localhost")
        with pytest.raises(requests.exceptions.ConnectionError):
            ss.login(TESTauth_uname, TESTauth_password)

    def test_is_logged_in01(self) -> None:
        retval = self.s.is_logged_in()
        assert isinstance(retval, bool), "bool expected"
        assert not retval, "expected False"

        # we are NOT logged in -- try to log out anyway
        with pytest.raises(RuntimeError):
            self.s.logout()

    def test_logout01(self) -> None:
        """Make sure we can login and out."""
        s = self.s
        isin = s.is_logged_in()
        assert isinstance(isin, bool), "bool epxected"
        assert not isin, "not isin expected"
        s.login(TESTauth_uname, TESTauth_password)
        # should have been successful
        isin = s.is_logged_in()
        assert isinstance(isin, bool), "bool epxected"
        assert isin, "isin expected"

        # now logout again
        s.logout()
        isin = s.is_logged_in()
        assert isinstance(isin, bool), "bool epxected"
        assert not isin, "isin expected"


@withqai
class SimpleQAItester:
    @classmethod
    def setup_class(cls) -> None:
        lverb = True
        if lverb:
            print("SETUP CLASS {}".format(cls))
        cls.faulty_session = FaultySession(TESTqai_url)
        # --
        cls.s = TrackerSession(TESTqai_url)
        cls.s.login(TESTauth_uname, TESTauth_password)
        if not cls.s.is_logged_in():
            raise RuntimeError("login failed")
        rcode, cls.reagent_list = cls.s.get_json(PATH_REAGENT_LIST_REAGENTS)
        assert rcode == HTTP_OK, "called failed"
        # get list of suppliers
        rcode, cls.supplierlst = cls.s.get_json(PATH_REAGENT_LIST_SUPPLIERS)
        assert rcode == HTTP_OK, "called failed"
        if lverb:
            yamlutil.writeyamlfile(cls.supplierlst, "./supplierlst.yaml")
        # lets choose a supplier from the list. Choose the first name in the list.
        cls.selected_supplier_dct = cls.supplierlst[0]
        # retrieve the list of locations and choose some for testing.
        rcode, cls.loclst = cls.s.get_json(PATH_LOCATION_LIST)
        assert rcode == HTTP_OK, "called failed"
        if lverb:
            yamlutil.writeyamlfile(cls.loclst, "./loclist.yaml")
        nameset = frozenset(['SPH\\604\\Research Fridge', 'SPH\\605\\Fridge'])
        cls.testlocs = [d for d in cls.loclst if d['name'] in nameset]
        if len(cls.testlocs) != len(nameset):
            print("loclst '{}'".format(cls.loclst))
            raise RuntimeError("error finding location names {}".format(nameset))
        cls.establish_test_reagent()

    @classmethod
    def establish_test_reagent(cls):
        lverb = True
        # next, retrieve the list of users and choose our testing user.
        rcode, userlst = cls.s.get_json(PATH_USER_LIST)
        assert rcode == HTTP_OK, "called failed"
        if lverb:
            yamlutil.writeyamlfile(userlst, "./userlst.yaml")
        cls.test_user_login = 'wscott'
        fndlst = [d for d in userlst if d['login'] == cls.test_user_login]
        if len(fndlst) != 1:
            print("userlst: {}".format(userlst))
            raise RuntimeError('failed to find test user')
        cls.test_user = fndlst[0]
        test_user_id = cls.test_user['id']
        cls.test_stat_lst = [
            {'status': 'MADE',
             'occurred': '1956-03-31T00:00:00Z',
             'qcs_user_id': test_user_id},
            {'status': 'EXPIRED',
             'occurred': '1956-03-31T00:00:00Z',
             'qcs_user_id': test_user_id},
            {'status': 'RUO_EXPIRED',
             'occurred': '1956-03-31T00:00:00Z',
             'qcs_user_id': test_user_id}]

        cls.test_reagent_item_lot_num = 'testlotAAA'
        cls.test_reagent_item_notes = "A fictitious stock item for software testing purposes"
        cls.test_itema_rfid = random_string(8)
        # --- create or retrieve a test reagent
        cls.test_reagent_name = "Whisky-Cola"
        cls.test_reagent_catnum = '9999'
        cls.test_reagent_id = None
        # if we have a reagent of this name, lets use it
        fndlst = [d for d in cls.reagent_list if d['name'] == cls.test_reagent_name]
        if len(fndlst) > 0:
            if lverb:
                print("found a test reagent {}".format(fndlst[0]))
            cls.test_reagent_id = fndlst[0]['id']
        else:
            pdct = {'basetype': 'stockchem',
                    'name': cls.test_reagent_name,
                    'category': 'Other Chemicals',
                    'notes': 'essential equipment',
                    'storage': '',
                    'needs_validation': None,
                    'expiry_time': 30,
                    'supplier': cls.selected_supplier_dct['name'],
                    'catalog_number': cls.test_reagent_catnum,
                    'date_msds_expires': 'never',
                    'msds_filename': ''}
            rcode, postres = cls.s.post_json(TPATH_REAGENT_SAVE, data=pdct, retries=1)
            if lverb:
                print("POSTreagent save {}".format(postres))
            assert rcode == HTTP_CREATED, "call failed"
            cls.test_reagent_id = postres['id']
        print("goot ID {}".format(cls.test_reagent_id))
        assert cls.test_reagent_id is not None, "cannot get test reagent id"

    @classmethod
    def get_reagent_item_record(cls, item_id, isrfid=False):
        """Retrieve the complete record of the test reagent.
        This routine uses qcs_reagent/show to retrieve the item.
        Raise a RuntimeError if anything goes wrong.
        """
        reagent_id = cls.test_reagent_id
        rcode, r_show = cls.s.get_json(PATH_REAGENT_SHOW, params=dict(id=reagent_id))
        if rcode != HTTP_OK:
            raise RuntimeError("get call failed")
        itm_lst = r_show['items']
        if len(itm_lst) == 0:
            raise RuntimeError("item list is zero")
        if isrfid:
            fndlst = [d for d in itm_lst if d['rfid'] == item_id]
        else:
            fndlst = [d for d in itm_lst if d['id'] == item_id]
        if len(fndlst) != 1:
            raise RuntimeError("itemid not found")
        return fndlst[0]

    @classmethod
    def setRFID(cls, item_id, new_RFID):
        rcode, res = cls.s.patch_json(TPATH_REAGENT_ITEM,
                                      data=dict(id=item_id, rfid=new_RFID))
        print("setRFID {}: {} -> {}".format(item_id, new_RFID, res))
        if rcode != HTTP_OK:
            raise RuntimeError("call failed, retcode={}\n".format(rcode))

    @classmethod
    def setlocation(cls, item_id, new_locid):
        rcode, res = cls.s.patch_json(TPATH_REAGENT_ITEM,
                                      data=dict(id=item_id, qcs_location_id=new_locid))
        print("setlocid {}: {} -> {}".format(item_id, new_locid, res))
        if rcode != HTTP_OK:
            raise RuntimeError("call failed, retcode={}\n".format(rcode))

    def setup_method(self) -> None:
        # print("setup method {}".format(self))
        assert self.s is not None, "s is none"
        assert self.reagent_list is not None, "reagentlist is none"

    def teardown_method(self) -> None:
        # we cannot remove test data
        # self.remove_test_reagent()
        pass


def random_string(len: int) -> str:
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(len))


@withqai
class Test_creation(SimpleQAItester):

    def test_logout_raises_01(self) -> None:
        self.faulty_session._islogged_in = True
        with pytest.raises(RuntimeError):
            self.faulty_session.logout()
        # assert False, "force fail"

    def test_is_logged_in02(self):
        retval = self.s.is_logged_in()
        assert isinstance(retval, bool), "bool expected"
        assert retval, "expected true"
        # r = self.s._rawget(PATH_REAGENT_LIST_SUPPLIERS)
        print("COOKIES {}".format(self.s.cookies.items()))
        # assert False, "force fail"

    @pytest.mark.skip(reason="A change on QAI made this test fail. not needed for now")
    def test_create_item01(self):
        """Try to create a reagent item. This should succeed."""
        test_itema_locid = self.testlocs[0]['id']
        test_rfid = random_string(6)
        print("setting new location to {}".format(test_itema_locid))
        itema = {'qcs_reag_id': self.test_reagent_id,
                 'qcs_location_id': test_itema_locid,
                 'lot_num': self.test_reagent_item_lot_num,
                 'notes': self.test_reagent_item_notes,
                 'rfid': test_rfid,
                 'source_ids': [],
                 'statuses': self.test_stat_lst}
        rcode, res = self.s.post_json(TPATH_REAGENT_ITEM, data={'items': [itema]})
        print("itema {}".format(itema))
        print("postres '{}'".format(res))
        assert rcode == HTTP_OK, "creation call failed"
        print("creation OK... now retrieve RFID = {}".format(test_rfid))
        itm_rec = self.get_reagent_item_record(test_rfid, isrfid=True)
        assert itm_rec['qcs_location_id'] == test_itema_locid, " locid mismatch"
        assert itm_rec['rfid'] == test_rfid, "rfid mismatch"

    @pytest.mark.skip(reason="A change on QAI made this test fail. not needed for now")
    def test_create_item_nolocation01(self):
        """Creating a reagent item without a location should fail."""
        # NOTE: test once without a location key, once with a value of None.
        itema = {'qcs_reag_id': self.test_reagent_id,
                 'lot_num': self.test_reagent_item_lot_num,
                 'notes': self.test_reagent_item_notes,
                 'source_ids': [],
                 'statuses': self.test_stat_lst}
        for i in range(2):
            test_rfid = random_string(6)
            itema['rfid'] = test_rfid
            rcode, res = self.s.post_json(TPATH_REAGENT_ITEM, data={'items': [itema]})
            print("itema {}".format(itema))
            print("postres '{}'".format(res))
            assert rcode != HTTP_OK, "creation call succeeded against expectations"
            with pytest.raises(RuntimeError):
                self.get_reagent_item_record(test_rfid, isrfid=True)
            # add the key for the next round..
            itema['qcs_location_id'] = None

    def test_create_reagent_fail01(self):
        """ Creation of a reagent with faulty input data should fail."""
        test_reagent_name = 'TEST' + random_string(5)
        testlst = []
        pdct1 = {'basetype': 'stockchem',
                 'name': test_reagent_name,
                 'category': 'Other Chemicals',
                 'notes': self.test_reagent_item_notes,
                 'storage': '',
                 'needs_validation': None,
                 'expiry_time': 10,
                 'supplier': self.selected_supplier_dct['name'],
                 'date_msds_expires': 'never'}
        # illegal basetype
        pdct2 = pdct1.copy()
        pdct2['basetype'] = 'WRONG_BASETYPE'
        testlst.append(pdct2)
        # illegal category
        pdct2 = pdct1.copy()
        pdct2['category'] = 'WRONG_CAT'
        testlst.append(pdct2)
        # illegal storage
        pdct2 = pdct1.copy()
        pdct2['storage'] = 'WRONG STORAGE'
        testlst.append(pdct2)
        # illegal validation
        pdct2 = pdct1.copy()
        pdct2['needs_validation'] = 'YES'
        testlst.append(pdct2)
        # illegal expiry_time
        pdct2 = pdct1.copy()
        pdct2['expiry_time'] = '2 years'
        testlst.append(pdct2)
        # illegal expiry_time
        pdct2 = pdct1.copy()
        pdct2['expiry_time'] = 'now'
        testlst.append(pdct2)
        for testnum, pdct in enumerate(testlst):
            rcode, postres = self.s.post_json(TPATH_REAGENT_SAVE, data=pdct, retries=1)
            print("PDCT #{}: {}".format(testnum, pdct))
            print("POSTRES rcode {}: {}".format(rcode, postres))
            assert rcode == HTTP_INTERNAL_SERVER_ERROR, "call should not have succeeded"
            print("\n\n")
        # this should pass
        testnum, pdct = -1, pdct1
        rcode, postres = self.s.post_json(TPATH_REAGENT_SAVE, data=pdct, retries=1)
        print("PDCT #{}: {}".format(testnum, pdct))
        print("POSTRES {}".format(postres))
        assert rcode == HTTP_CREATED, "call should have succeeded"
        # assert False, "force fail"

    def test_reagent_receive(self):
        test_locid = self.testlocs[1]['id']
        rfidlst = ['RFID' + random_string(6) for i in range(4)]
        pdct = {'location_id': test_locid, 'rfids': rfidlst}
        print("RECEIVE: {}".format(pdct))
        # assert False, "force fail"
        r = self.s._rawget(PATH_REAGENT_RECEIVE, params=pdct)
        url = r.url
        print("the URL IS {}".format(url))
        # assert False, "force fail"

    def test_gen_receive_url01(self):
        """Generating a receive URL with an empty rfidlst should raise an exception."""
        test_locid = self.testlocs[1]['id']
        for rfidlst in [None, []]:
            for isnew in [True, False]:
                with pytest.raises(RuntimeError):
                    self.s.generate_receive_url(test_locid, rfidlst, isnew)

    def test_gen_receive_url02(self):
        """Create a receive URL for existing and missing loc_ids"""
        rfidlst = ['RFID' + random_string(6) for i in range(2)]
        for test_locid in [None, 9999]:
            for isnew in [True, False]:
                urlstr = self.s.generate_receive_url(test_locid, rfidlst, isnew)
                assert isinstance(urlstr, str), "string expected"
                print("the URL IS {}".format(urlstr))
        # assert False, "force fail"


@withqai
class DATAQAItester(SimpleQAItester):
    """An abstract base class that sets up the QAI access and ensures test data
    is in place. The actual tests are run in the subclasses."""
    @classmethod
    def setup_class(cls) -> None:
        super().setup_class()
        cls.create_test_reagent()

    @classmethod
    def create_test_reagent(cls) -> None:
        """Create some test data to play with.
        If the following do not already exist in the database, we
        create a reagent, and a reagent item.
        """
        lverb = True
        rcode, cls.reagent_dct = cls.s.get_json(PATH_REAGENT_LIST)
        assert rcode == HTTP_OK, "called failed"
        if lverb:
            yamlutil.writeyamlfile(cls.reagent_dct, "./reagentlst.yaml")
        cls.reagent_lst = cls.reagent_dct['items']
        cls.establish_test_reagent()
        # --- create some reagent items
        # see whether we have a reagent item with this rfid: create one if not, and set
        # the item_id
        cls.test_itema_id = None
        cls.test_itema_locid = None
        rcode, reagitemlst = cls.s.get_json(PATH_REAGITEM_LIST,
                                            params=dict(id=cls.test_reagent_id))
        assert rcode == HTTP_OK, "call to PATH_REAGITEM_LIST failed"
        if lverb:
            yamlutil.writeyamlfile(reagitemlst, "./reagitemlst.yaml")
        fndlst = [d for d in reagitemlst if d['rfid'] == cls.test_itema_rfid]
        if len(fndlst) == 0:
            # if there are items, but not one with the expected RFID, then modify the RFID
            # of a record
            cls.test_itema_locid = cls.testlocs[0]['id']
            if len(reagitemlst) > 0:
                print("setting location")
                cls.setlocation(reagitemlst[0]['id'], cls.test_itema_locid)
                print("SETTING RFID\n")
                cls.setRFID(reagitemlst[0]['id'], cls.test_itema_rfid)
            else:
                # create a reagent item
                print("setting new location to {}".format(cls.test_itema_locid))
                itema = {'rfid': cls.test_itema_rfid,
                         'qcs_reag_id': cls.test_reagent_id,
                         'qcs_location_id': cls.test_itema_locid,
                         'lot_num': cls.test_reagent_item_lot_num,
                         'notes': cls.test_reagent_item_notes,
                         'source_ids': [],
                         'statuses': cls.test_stat_lst}
                rcode, res = cls.s.post_json(TPATH_REAGENT_ITEM, data={'items': [itema]})
                assert rcode == HTTP_CREATED, "called failed"
                print("postres '{}'".format(res))
            itm_rec = cls.get_reagent_item_record(cls.test_itema_rfid, isrfid=True)
            cls.test_itema_id = itm_rec['id']
            print('LOC2 {}'.format(itm_rec))
            # raise RuntimeError("Stopping for a test")
        else:
            print("Found item with required RFID")
            assert len(fndlst) == 1, "Database Error: multiple items with same RFID"
            # ensure the required state of an existing reagent item
            print("BLAREC {}".format(fndlst[0]))
            cls.test_itema_id = fndlst[0]['id']
            print("looking for item {}".format(cls.test_itema_id))
            itm_rec = cls.get_reagent_item_record(cls.test_itema_id)
            print("Found required item")
            # ensure that the reagent item is MADE, not IN_USE
            if itm_rec['current_status'] == 'IN_USE':
                res = cls.s.delete_json(PATH_REAGITEM_STATUS,
                                        params=dict(qcs_reag_item_id=cls.test_itema_id,
                                                    status='IN_USE'))
                print("got res {}".format(res))
                itm_rec = cls.get_reagent_item_record(cls.test_itema_id)
            assert itm_rec['current_status'] == 'MADE', 'made status expected'
            cls.test_itema_locid = itm_rec['loc_id']
            # ensure the RFID is what the tests expected
            # if itm_rec['rfid'] != cls.test_itema_rfid:
            #    rcode, res = cls.s.patch_json(TPATH_REAGENT_ITEM,
            #                                  data=dict(id=cls.test_itema_id,
            #                                            rfid=cls.test_itema_rfid))
            #    assert rcode == HTTP_OK, "called failed"
            #    itm_rec = cls.get_reagent_item_record(cls.test_itema_id)
            assert itm_rec['rfid'] == cls.test_itema_rfid, "failed to set RFID"
        print("ITEMREC IS {}".format(itm_rec))
        if itm_rec['loc_id'] is None:
            print("setting item location")
            cls.test_itema_locid = cls.testlocs[0]['id']
            cls.setlocation(cls.test_itema_id, cls.test_itema_locid)
        assert cls.test_itema_id is not None, "failed to determine itema_id"
        assert cls.test_itema_locid is not None, "failed to determine itema_locid"
        # raise RuntimeError("force fail")


@withqai
class Test_qai_helper_get(DATAQAItester):
    """These tests are performed after a valid log in has been performed.
    They only perform get operations (i.e. do not modify the test database)
    """

    def test_illegalurl01(self):
        """An illegal URL should raise an exception"""
        # NOTE: we have omitted the leading backslash
        invalid_url = PATH_LOCATION_LIST[1:]
        with pytest.raises(requests.exceptions.InvalidURL):
            self.s.get_json(invalid_url)

    def test_get_location_list01(self):
        """Getting the list of locations should be of
        the expected data structure."""
        # loclst = self.loclst
        loclst = self.s._get_location_list()
        assert isinstance(loclst, list), 'list expected'
        tdct = {'id': int, 'name': str}
        for d in loclst:
            check_dct_type(tdct, d)
        #
        with pytest.raises(RuntimeError):
            self.faulty_session._get_location_list()

    def test_get_supplier_list(self) -> None:
        supplst = self.s._get_supplier_list()
        assert isinstance(supplst, list), 'list expected'
        with pytest.raises(RuntimeError):
            self.faulty_session._get_supplier_list()

    def test_get_reagent_list01(self) -> None:
        rlst = self.s._get_reagent_list()
        assert isinstance(rlst, list), 'list expected'
        with pytest.raises(RuntimeError):
            self.faulty_session._get_reagent_list()

    def test_get_reagent_list02(self):
        """Getting the reagent list should succeed and provide
        the expected data structure."""
        lverb = True
        rcode, rjson = self.s.get_json(PATH_REAGENT_LIST)
        assert rcode == HTTP_OK, "called failed"
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
        """Find all reagents at a specific location"""
        lverb = False
        selected_loc = self.testlocs[0]
        loc_id = selected_loc['id']
        loc_name = selected_loc['name']
        query_dct = {'id': loc_id}
        if lverb:
            print("search for reagents at locid {}: '{}'".format(loc_id, loc_name))
        rcode, rlst = self.s.get_json(PATH_REAGENT_LOCITEMS, params=query_dct)
        assert rcode == HTTP_OK, "call failed"
        if lverb:
            print("goot {}".format(rlst))
            for dat, fn in [(rlst, "./locitems.yaml")]:
                yamlutil.writeyamlfile(dat, fn)
        # assert False, "force fail"

    def test_reagent_list_and_show01(self):
        """Get information about a specific reagent"""
        lverb = True
        reagent_id = self.test_reagent_id
        reagent_name = self.test_reagent_name
        pdct = {'id': reagent_id}
        rcode, reagent_show = self.s.get_json(PATH_REAGENT_SHOW, params=pdct)
        assert rcode == HTTP_OK, "call failed"
        if lverb:
            print("showing reagent: '{}: '{}".format(reagent_id, reagent_name))
            for dat, fn in [(reagent_show, "./reagentshow.yaml")]:
                yamlutil.writeyamlfile(dat, fn)

    # The tests below this line perform get, put and patch operations (i.e. the test
    # database is modified)

    def get_reagent_item(self, item_id):
        """We want to retrieve the current state of a reagent item.
        we get the items of the test reagent and then select for the item"""
        rcode, itm_lst = self.s.get_json(PATH_REAGITEM_LIST,
                                         params={'reagent_id': self.test_reagent_id})
        assert rcode == HTTP_OK, "called failed"
        fndlst = [d for d in itm_lst if d['id'] == item_id]
        assert len(fndlst) == 1, "itemid not found"
        return fndlst[0]

    def test_get_reagent_items01(self):
        """Attempt to get all reagent items defined."""
        rcode, itm_lst = self.s.get_json(PATH_REAGITEM_LIST)
        assert rcode == HTTP_OK, "called failed"

    def test_get_reagent_items02(self):
        """Attempt to get all reagent items defined."""
        itm_dct = self.s._get_reagent_items([])
        assert isinstance(itm_dct, dict), "dict expected"
        assert len(itm_dct) == 0, "expecting empty dict"

        itm_dct = self.s._get_reagent_items([dict(id=self.test_reagent_id)])
        assert isinstance(itm_dct, dict), "dict expected"
        assert len(itm_dct) == 1, "expecting empty dict"
        with pytest.raises(RuntimeError):
            self.faulty_session._get_reagent_items([dict(id=self.test_reagent_id)])

    def test_reagent_item_patch01(self):
        """We should be able to modify a reagent_item."""
        # lets try to change the RFID...
        # a: make sure the item with the expected RFID is present
        item_id = self.test_itema_id
        org_RFID = self.test_itema_rfid
        print("TRYING {}".format(PATH_REAGITEM_LIST))
        org_state = self.get_reagent_item(item_id)
        assert org_state['rfid'] == org_RFID, "unexpected RFID 1"

        # b: try and change the RFID, and then back again
        test_RFID = org_RFID + 'C'
        for new_RFID in [test_RFID, org_RFID]:
            print("patching: {} to RFID={}".format(TPATH_REAGENT_ITEM, new_RFID))
            rcode, res = self.s.patch_json(TPATH_REAGENT_ITEM,
                                           data=dict(id=item_id, rfid=new_RFID))
            if rcode != HTTP_OK:
                print("RESMUT A {}".format(res))
                raise RuntimeError("call failed, retcode={}\n".format(rcode))
            # c: read it back and make sure the change worked
            new_state = self.get_reagent_item(item_id)
            assert new_state['rfid'] == new_RFID, "unexpected RFID 2"

    def test_reagent_path01(self):
        """We should be able to modify a reagent item.
        patch TPATH_REAGENT_SAVE
        """
        lverb = True
        # lets try and change the catalogue number
        for catnum in ['1234', self.test_reagent_catnum]:
            pdct = {"id": self.test_reagent_id,
                    'catalog_number': catnum}
            rcode, res = self.s.patch_json(TPATH_REAGENT_SAVE, data=pdct)
            assert rcode == HTTP_OK, "called failed"
            if lverb:
                print("POSTreagent save {}".format(res))

    @pytest.mark.skip(reason="this test needs to be reworked: semantics of item status has changed")
    def test_reagent_item_status01(self):
        """It should be possible to update the status of a reagent item.
        post PATH_REAGITEM_STATUS
        and also delete the status with:
        delete PATH_REAGITEM_STATUS
        """
        lverb = True
        item_id = self.test_itema_id
        org_RFID = self.test_itema_rfid
        print("TRYING {}".format(PATH_REAGITEM_LIST))
        org_rec = self.get_reagent_item_record(item_id)
        if lverb:
            print("ORG_REC {}".format(org_rec))
        assert org_rec['rfid'] == org_RFID, "unexpected RFID 1"
        org_state = org_rec['current_status']
        # the state should be MADE, so that we can try to change it....
        # however, this could be the result of a previous, failed test run...
        change_time = '1956-03-31T10:00:00Z'
        if org_state != 'MADE':
            print("reagent item state is expected to be 'MADE'.. resetting")
            upd_dct = {'rfid': org_RFID,
                       'status': 'MADE',
                       'occurred': change_time}
            rcode, res = self.s.post_json(PATH_REAGITEM_STATUS, data=upd_dct)
            org_rec = self.get_reagent_item_record(item_id)
            if lverb:
                print("ORG_REC 2 {}".format(org_rec))
        org_state = org_rec['current_status']
        assert org_state == 'MADE', "reagent item is not MADE...aborting test"
        new_state = 'IN_USE'
        upd_dct = {'rfid': org_RFID,
                   'status': new_state,
                   'occurred': change_time}
        rcode, res = self.s.post_json(PATH_REAGITEM_STATUS, data=upd_dct)
        if rcode != HTTP_CREATED:
            print("call failed with rcode={}, {}".format(rcode, requests.codes[rcode]))
            print("got post res {}".format(res))
            raise RuntimeError("unexpected rcode")
        exp_msg = 'Item(s) set as IN_USE'
        if res['message'] != exp_msg:
            raise RuntimeError("change status failed {}".format(res))
        itm_rec = self.get_reagent_item_record(self.test_itema_id)
        if itm_rec['current_status'] != new_state:
            raise RuntimeError("new status {} not set to {}".format(itm_rec['current_status'],
                                                                    new_state))
        if itm_rec['current_status_occurred'] != change_time:
            raise RuntimeError("new change date {} is not expected {}".format(itm_rec['current_status_occurred'],
                                                                              change_time))
        if lverb:
            print("AFTER UPD {}".format(itm_rec))
        # now delete the last status change again
        rcode, res = self.s.delete_json(PATH_REAGITEM_STATUS,
                                        params=dict(qcs_reag_item_id=item_id,
                                                    status=new_state))
        assert rcode == HTTP_OK, "called failed"
        if lverb:
            print("delete res {}".format(res))
        if res['message'] != 'OK':
            raise RuntimeError("delete status failed {}".format(res))
        itm_rec = self.get_reagent_item_record(item_id)
        assert itm_rec['current_status'] == 'MADE', 'made status expected'
        # assert False, "force fail"

    def test_verify_location01(self):
        """ Update the reagent item id's at a location.
        patch PATH_REAGENT_VERIFY_LOCATION
        """
        lverb = True
        # ensure preconditions are met
        item_id = self.test_itema_id
        locId = self.test_itema_locid
        org_rec = self.get_reagent_item_record(item_id)
        assert org_rec['loc_id'] == locId, "unexpected location"
        # now change the item_ids at the location
        mod_dct = {'location_id': locId,
                   'remove_ids': [],
                   'add_ids': [item_id],
                   }
        rcode, res = self.s.patch_json(PATH_REAGENT_VERIFY_LOCATION, data=mod_dct)
        if lverb:
            print("res VER2 {}".format(res))
        assert rcode == HTTP_OK, "called failed"

    def test_changedata(self):
        d = self.s.get_qai_changedata()
        assert isinstance(d, dict), "dict expected"
        print("BLA {}".format(d))
        with pytest.raises(RuntimeError):
            self.faulty_session.get_qai_changedata()

    def test_qai_dump01(self):
        with pytest.raises(RuntimeError):
            self.faulty_session.get_qai_dump()

    def test_clever_qai_update_args(self):
        """Passing wrongs args to the routine should raise a RuntimeError
        No QAI server access is required for this test.
        """
        # create a faulty tsdct (missing keys)
        rdct: qai_helper.QAIdct = None
        tsdct: qai_helper.QAIChangedct = {}
        qaids = qai_helper.QAIDataset(rdct, tsdct)
        with pytest.raises(RuntimeError):
            self.s.clever_update_qai_dump(qaids)
        # now try again with a better tsdct..
        for k in qai_helper.QAISession.qai_key_lst:
            tsdct[k] = 'now'
        qaids = qai_helper.QAIDataset(rdct, tsdct)
        # a faulty session
        with pytest.raises(RuntimeError):
            self.faulty_session.clever_update_qai_dump(qaids)


@dumpchemstock
class Test_dump:

    @classmethod
    def setup_class(cls) -> None:
        lverb = True
        if lverb:
            print("SETUP CLASS {}".format(cls))
        cls.s = TrackerSession(TESTqai_url)
        cls.s.login(TESTauth_uname, TESTauth_password)
        if not cls.s.is_logged_in():
            raise RuntimeError("login failed")

    # @pytest.mark.skip(reason="Takes too long")
    def test_qai_dump02(self):
        ds = self.s.get_qai_dump()
        assert isinstance(ds, qai_helper.QAIDataset), "QAIDataset expected"
        yamlutil.writeyamlfile(ds, QAI_DUMP_FILE)
