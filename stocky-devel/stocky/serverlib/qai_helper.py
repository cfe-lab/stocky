import json
import logging
from random import Random
import requests
import time
import typing

logger = logging.getLogger('qai_helper')


StatusCode = int

RequestValue = typing.Tuple[StatusCode, typing.Any]


def tojson(data) -> str:
    """Convert the data structure to json.
    see https://docs.python.org/3.4/library/json.html
    """
    try:
        retstr = json.dumps(data, separators=(',', ':'), default=str)
    except TypeError as e:
        logger.warn("problem converting to json '{}'".format(data))
        raise e
    return retstr


def fromjson(data_bytes: bytes) -> typing.Any:
    """Convert bytes into a data struct which we return.
    This routine will raise an exception of there is an error in json.loads
    """
    return json.loads(data_bytes)


def safe_fromjson(data_bytes: bytes) -> typing.Optional[typing.Any]:
    """Convert bytes into a data struct which we return.
    This routine will return None if the conversion from json fails.
    """
    try:
        return json.loads(data_bytes)
    except json.decoder.JSONDecodeError:
        return None


class Session(requests.Session):

    def __init__(self) -> None:
        super().__init__()
        self._islogged_in = False

    def _login_resp(self, qai_path: str, qai_user: str, password: str) -> requests.Response:
        self.qai_path = qai_path
        return self.post(qai_path + "/account/login",
                         data={'user_login': qai_user,
                               'user_password': password})

    def login(self, qai_path: str, qai_user: str, password: str) -> None:
        """ Login to QAI before calling post_json or get_json.
        @raise RuntimeError: when the QAI server rejects the user and password.
        """
        response = self._login_resp(qai_path, qai_user, password)
        if response.status_code == requests.codes.forbidden:  # @UndefinedVariable
            raise RuntimeError("Login failed for QAI user '{}'.".format(qai_user))
        self._islogged_in = True

    def login_try(self, qai_path: str, qai_user: str, password: str) -> dict:
        """Try to login. Do not raise any exceptions, byt return a dict with information
        that can be shown to the user.
        The dict returned must have:
        "username": return the name of the user
        "ok" boolean
        if not ok:
          msg = "error message for the user"
        """
        if qai_user is None:
            return dict(ok=False, msg="Configuration error: empty username")
        if password is None:
            return dict(ok=False, msg="Configuration error: empty password")
        try:
            response = self._login_resp(qai_path, qai_user, password)
        except requests.exceptions.InvalidURL:
            return dict(ok=False, msg="Configuration error: invalid QAI URL {}".format(qai_path))
        except requests.exceptions.HTTPError:
            return dict(ok=False, msg="Configuration error: HTTP Protocol error")
        except Exception:
            # the QAI could not be contacted (exceeded number of attempts)
            return dict(ok=False,
                        msg="Login unsuccessful: The QAI system at {} cannot be contacted".format(qai_path))
        retstat = response.status_code
        if retstat == requests.codes.forbidden:
            return dict(ok=False,
                        msg="Login unsuccessful: The QAI system refused access for user {}".format(qai_user))
        # finally -- things seem to have worked out
        self._islogged_in = True
        return dict(ok=True,
                    msg="Access granted for user {}".format(qai_user),
                    username=qai_user)

    def is_logged_in(self):
        return self._islogged_in

    def _retry_response(self,
                        method,
                        path: str,
                        data: typing.Any=None,
                        params: dict=None,
                        retries: int=3,
                        expect_json: bool=True) ->requests.Response:
        if not self._islogged_in:
            raise RuntimeError("Must log in before using the call API")
        json_data = data and tojson(data)
        # json_data = data and json.dumps(data)
        if expect_json:
            headers = {'Accept': 'application/json'}
        else:
            headers = {'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
        if json_data:
            headers['Content-Type'] = 'application/json'
        else:
            headers['Content-Type'] = 'text/plain;charset=utf-8'
        # print("RRR expect_json {}, json_data: {}".format(expect_json, json_data))
        retries_remaining = retries
        average_delay = 20
        while True:
            try:
                response = method(
                    self.qai_path + path,
                    data=json_data,
                    params=params,
                    headers=headers)
                # 2018-07-05: QAI will in general return 500 when it is unhappy
                # with an attempted operation (e.g. when using POST to create
                # a reagent that already exists). This is not quite comme-il-faut, but
                # we have to live with it for now. We do not want to raise an
                # exception here in such a case, but allow the higher ups to handle
                # the error messages contained in the returned json data.
                # response.raise_for_status()
                return response
            # in some cases, we should not retry, but give up right away.
            except requests.exceptions.InvalidURL:
                raise
            except requests.exceptions.HTTPError:
                raise
            except Exception:
                if retries_remaining <= 0:
                    logger.error('JSON request failed for %s',
                                 path,
                                 exc_info=True)
                    raise

                # ten minutes with some noise
                sleep_seconds = average_delay + Random().uniform(-10, 10)
                logger.warn(
                    'JSON request failed. Sleeping for %ss before retry.',
                    sleep_seconds,
                    exc_info=True)
                time.sleep(sleep_seconds)
                retries_remaining -= 1
                average_delay += 600

    def _retry_json(self, method, path, data=None, params=None, retries=3) -> RequestValue:
        r = self._retry_response(method, path, data=data, params=params, retries=retries)
        return (r.status_code, r.json())

    def patch_json(self, path: str, data: typing.Any, params=None, retries=3) -> RequestValue:
        return self._retry_json(self.patch, path, data=data, params=params, retries=retries)

    def post_json(self, path: str, data: typing.Any, retries=3) -> RequestValue:
        """ Post a JSON object to the web server, and return a JSON object.

        @param path the relative path to add to the qai_path used in login()
        @param data a JSON object that will be converted to a JSON string
        @param retries: the number of times to retry the request before failing.
        @return the response body, parsed as a JSON object
        """
        return self._retry_json(self.post, path, data=data, retries=retries)

    def generate_receive_url(self, locid: int, rfidlst: typing.List[int]) -> str:
        """Generate the URL in string form that can be used to generate
        a RFID receive response.
        """
        if rfidlst is None or len(rfidlst) == 0:
            raise RuntimeError("Empty rfidlst")
        ustr = self.qai_path + PATH_REAGENT_RECEIVE
        qstr = "?location_id={}".format(locid)
        rstr = "".join(["&rfids={}".format(rfid) for rfid in rfidlst])
        return ustr + qstr + rstr

    def _rawget(self, path: str, params: dict=None, retries=3) -> requests.Response:
        """Perform a get call to the server, in which we do NOT expect a json response
        from the server.
        """
        return self._retry_response(self.get,
                                    path,
                                    params=params,
                                    retries=retries,
                                    expect_json=False)

    def get_json(self, path: str, params: dict=None, retries=3) -> RequestValue:
        """ Get a JSON object from the web server.

        @param session an open HTTP session
        @param path the relative path to add to settings.qai_path
        @param retries: the number of times to retry the request before failing.
        @return the response body, parsed as a JSON object
        """
        return self._retry_json(self.get, path, params=params, retries=retries)

    def delete_json(self, path: str, params: dict=None, retries=3) -> RequestValue:
        return self._retry_json(self.delete, path, params=params, retries=retries)


# -- the following endpoints are part of the 'official' API that can be used
# by stocky
# -- location. We only have a get
PATH_LOCATION_LIST = '/qcs_location/list'


# -- reagent operations
# reagent get
PATH_REAGENT_LIST = '/qcs_reagent/list'
PATH_REAGENT_LIST_REAGENTS = '/qcs_reagent/list_reagents'
PATH_REAGENT_LOCITEMS = '/qcs_reagent/location_items'
PATH_REAGENT_SHOW = '/qcs_reagent/show'
PATH_REAGENT_RECEIVE = '/qcs_reagent/receive'

# reagent patch
PATH_REAGENT_VERIFY_LOCATION = '/qcs_reagent/verify_location'

# -- reagent items ---
# reagent item get
PATH_REAGITEM_LIST = '/qcs_reagent/list_reagent_items'

# reagent item post
PATH_REAGITEM_STATUS = '/qcs_reagent/item_status'

# suppliers
PATH_REAGENT_LIST_SUPPLIERS = '/qcs_reagent/list_suppliers'

# user list
PATH_USER_LIST = '/qcs_user/list'


# -- these are the DUMP URLs
DUMP_REAGENTS = '/table_dump/qcs_reag'
DUMP_REAG_ITEMS = '/table_dump/qcs_reag_item'
DUMP_REAG_ITEM_STATUS = '/table_dump/qcs_reag_item_status'
DUMP_REAG_ITEM_COMPOSITION = '/table_dump/qcs_reag_composition'
DUMP_LOCATION = '/table_dump/qcs_location'
DUMP_USERS = '/table_dump/qcs_users'

HTTP_OK = requests.codes.ok
HTTP_CREATED = requests.codes.created


QAIdct = typing.Dict[str, typing.Any]
QAIChangedct = typing.Dict[str, str]
QAIUpdatedct = typing.Dict[str, bool]


class QAIDataset:
    def __init__(self, qaidct: QAIdct, tsdct: QAIChangedct) -> None:
        self._qaidct = qaidct
        self._tsdct = tsdct

    def get_data(self) -> QAIdct:
        return self._qaidct

    def get_timestamp(self) -> QAIChangedct:
        return self._tsdct


class QAISession(Session):
    """Add some QAI- API-specific functions"""

    # these are entries in the QAIdct
    QAIDCT_REAGENTS = 'reagents'
    QAIDCT_REAGENT_ITEMS = 'reagent_items'
    QAIDCT_REAITEM_STATUS = 'reagent_item_status'
    QAIDCT_REAITEM_COMPOSITION = 'reagen_item_composition'
    QAIDCT_LOCATIONS = 'locations'
    QAIDCT_USERS = 'users'

    data_url_lst = [(QAIDCT_REAGENTS, DUMP_REAGENTS),
                    (QAIDCT_REAGENT_ITEMS, DUMP_REAG_ITEMS),
                    (QAIDCT_REAITEM_STATUS, DUMP_REAG_ITEM_STATUS),
                    (QAIDCT_REAITEM_COMPOSITION, DUMP_REAG_ITEM_COMPOSITION),
                    (QAIDCT_LOCATIONS, DUMP_LOCATION),
                    (QAIDCT_USERS, DUMP_USERS)]

    timestamp_url_lst = [(k, "%s//scn" % u) for k, u in data_url_lst]
    qai_key_lst = [k for k, u in data_url_lst]
    qai_key_set = frozenset(qai_key_lst)

    def _get_location_list(self) -> typing.List[dict]:
        """Retrieve a list of all locations.
        The dict contains two keys: id and name.
        """
        rcode, loclst = self.get_json(PATH_LOCATION_LIST)
        if rcode != HTTP_OK:
            raise RuntimeError("call for location_list failed")
        return loclst

    def _get_supplier_list(self) -> typing.List[str]:
        """Retrieve a list of reagent suppliers as a list of strings."""
        rcode, supplierlst = self.get_json(PATH_REAGENT_LIST_SUPPLIERS)
        if rcode != HTTP_OK:
            raise RuntimeError("call for supplier_list failed")
        return supplierlst

    def _get_reagent_list(self) -> typing.List[dict]:
        """Retrieve a list of all reagents.
        The dict contains two keys: id and name.
        """
        rcode, reagent_lst = self.get_json(PATH_REAGENT_LIST_REAGENTS)
        if rcode != HTTP_OK:
            raise RuntimeError("call for reagent_lst failed")
        return reagent_lst

    def _get_reagent_items(self, reagent_lst: typing.List[dict]) -> typing.Dict[int, dict]:
        """Retrieve the reagent items for each reagent dict provided.
        Return a dict with the reagent_id as a key, the value is a dict resulting
        from the show API call. (I.e. the reagent_items a list in "items", e.g.:
        reag_dct = get_reagent_items(rlst)
        my_reag_item_lst = reag_dct[my_reagent_id]['items']
        """
        rdct = {}
        for reagent_dct in reagent_lst:
            reag_id = reagent_dct['id']
            rcode, r_show = self.get_json(PATH_REAGENT_SHOW, params=dict(id=reag_id))
            if rcode != HTTP_OK:
                raise RuntimeError("call for reagent_show id={}  failed".format(reag_id))
            rdct[reag_id] = r_show
        return rdct

    def get_QAI_ChangeData(self) -> QAIChangedct:
        """Retrieve the current QAI change value (Oracle's system change number)
        for each data table we track.
        """
        rdct: QAIChangedct = {}
        for k, url in self.timestamp_url_lst:
            # print("TRYING {} {}".format(k, url))
            resp = self._rawget(url)
            rcode = resp.status_code
            rval = resp.text
            # print("BLARESP rcode: {}, cont {}".format(rcode, rval))
            if rcode != HTTP_OK:
                raise RuntimeError("call {}  failed with status {}".format(url, rcode))
            rdct[k] = rval
        return rdct

    def get_QAI_dump(self) -> QAIDataset:
        """Retrieve the complete reagent database as a QAIDataset.
        """
        rdct: QAIdct = {}
        for k, url in self.data_url_lst:
            rcode, rval = self.get_json(url)
            if rcode != HTTP_OK:
                raise RuntimeError("call for {} ({}) failed".format(k, url))
            rdct[k] = rval
        tsdct = self.get_QAI_ChangeData()
        return QAIDataset(rdct, tsdct)

    def clever_update_QAI_dump(self, qaiDS: QAIDataset) -> QAIUpdatedct:
        """Using the timestamp keys in tsdct, update those
        entries in qaidct and tsdct from the server that are out of date.
        For each dictionary entry (i.e. database table) return a
        boolean "an update from the server occured"
        """
        tsdct = qaiDS.get_timestamp()
        qaidct = qaiDS.get_data()
        for tdct in [tsdct, qaidct]:
            if set(tdct.keys()) != self.qai_key_set:
                raise RuntimeError("dct has wonky keys {}".format(tdct.keys()))
        newtsdct = self.get_QAI_ChangeData()
        retdct: QAIUpdatedct = {}
        for k, dataurl in self.data_url_lst:
            new_timestamp = newtsdct[k]
            do_update = retdct[k] = new_timestamp != tsdct[k]
            if do_update:
                # we need to update from the server
                rcode, rval = self.get_json(dataurl)
                if rcode != HTTP_OK:
                    raise RuntimeError("call for {} ({}) failed".format(k, dataurl))
                qaidct[k] = rval
                tsdct[k] = new_timestamp
        return retdct
