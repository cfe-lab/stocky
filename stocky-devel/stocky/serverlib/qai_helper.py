"""Implement a client-side http API to a QAI server for chemical stocks."""

import json
import logging
from random import Random
import requests
import time
import typing

logger = logging.getLogger('qai_helper')


StatusCode = int

RequestValue = typing.Tuple[StatusCode, typing.Any]


def tojson(data: typing.Any) -> str:
    """Convert a python data structure to json.

    The conversion typically occurs when sending a python data structure
    to the QAI via HTTP.
    See https://docs.python.org/3.4/library/json.html

    Args:
       data: the python data structure to convert.
    Returns:
       a json string representing the python data structure
    Raises:
       TypeError: if the data contains a structure that cannot be serialised.
    """
    try:
        retstr = json.dumps(data, separators=(',', ':'), default=str)
    except TypeError as e:
        logger.warning("problem converting to json '{}'".format(data))
        raise e
    return retstr


def fromjson(data_bytes: bytes) -> typing.Any:
    """Convert bytes to a python data structure.

    Convert json code in byte form, typically received from a QAI request,
    into a data struct which we return.

    Args:
       data_bytes: in the input JSON bytes
    Returns:
       The converted python data structure.
    Raises:
       This routine will raise an exception if a json conversion error occurs.
    """
    return json.loads(data_bytes)


def safe_fromjson(data_bytes: bytes) -> typing.Optional[typing.Any]:
    """Convert bytes to a python data structure.

    Convert json code in byte form, typically received from a QAI request,
    into a data struct which we return.

    Args:
       data_bytes: in the input JSON bytes
    Returns:
       The converted python data structure upon successful conversion.
       None is returned if an error occurred during conversion.
    """
    try:
        return json.loads(data_bytes)
    except json.decoder.JSONDecodeError:
        return None


class Session(requests.Session):

    def __init__(self, qai_path: str) -> None:
        """
        Args:
           qai_path: the base string to be used to contact the QAI server.
        """
        super().__init__()
        self._islogged_in = False
        self.qai_path = qai_path

    def _login_resp(self, qai_user: str, password: str) -> requests.Response:
        """In this routine, we call self.post directly.. therefore we
        should have a timeout that we catch in the calling routines...
        """
        TEN_SECONDS = 10
        return self.post(self.qai_path + "/account/login",
                         data={'user_login': qai_user,
                               'user_password': password},
                         timeout=TEN_SECONDS)

    def login(self, qai_user: str, password: str) -> None:
        """Login to the QAI system.

        Note: this must occur before calling any of the other API calls.

        Args:
           qai_user: the user name on the QAI system.
           password: the user's password.
        Raises:
           RuntimeError: when the QAI server rejects the user and password.
        """
        response = self._login_resp(qai_user, password)
        if response.status_code == requests.codes.forbidden:  # @UndefinedVariable
            raise RuntimeError("Login failed for QAI user '{}'.".format(qai_user))
        self._islogged_in = True

    def login_try(self, qai_user: str, password: str) -> dict:
        """Try to login without raising any exceptions.

        Instead, return a dict with information that can be shown to the
        user on the webclient.

        Returns:
           The dict returned must have the following keys
             1. "username": return the name of the user
             2. "ok": boolean
             3. if not ok, also msg = "error message for the user"
        """
        if qai_user is None:
            return dict(ok=False, msg="Configuration error: empty username")
        if password is None:
            return dict(ok=False, msg="Configuration error: empty password")
        try:
            response = self._login_resp(qai_user, password)
        except requests.exceptions.InvalidURL:
            return dict(ok=False, msg="Configuration error: invalid QAI URL: '{}'".format(self.qai_path))
        except requests.exceptions.ConnectionError:
            return dict(ok=False, msg="No route to host or connection refused (QAI URL: '{}')".format(self.qai_path))
        except requests.exceptions.HTTPError:
            return dict(ok=False, msg="Configuration error: HTTP Protocol error")
        except requests.exceptions.Timeout:
            return dict(ok=False, msg="The connection to QAI ({}) timed out".format(self.qai_path))
        except Exception:
            # the QAI could not be contacted (exceeded number of attempts)
            return dict(ok=False,
                        msg="Login unsuccessful: The QAI system at '{}' cannot be contacted".format(self.qai_path))
        retstat = response.status_code
        if retstat == requests.codes.forbidden:
            return dict(ok=False,
                        msg="Login unsuccessful: The QAI system at {} refused access for user {}".format(self.qai_path,
                                                                                                         qai_user))
        # finally -- things seem to have worked out
        self._islogged_in = True
        return dict(ok=True,
                    msg="Access granted for user {}".format(qai_user),
                    username=qai_user)

    def logout(self) -> None:
        """Perform a logout from QAI."""
        url = "/account/logout"
        resp = self._rawget(url)
        rcode = resp.status_code
        if rcode != HTTP_OK:
            raise RuntimeError("call {}  failed with status {}".format(url, rcode))
        self._islogged_in = False

    def is_logged_in(self):
        """
        Returns:
           whether a successful login to QAI has been performed.
        """
        return self._islogged_in

    def _retry_response(self,
                        method,
                        path: str,
                        data: typing.Any = None,
                        params: dict = None,
                        retries: int = 3,
                        expect_json: bool = True) ->requests.Response:
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
            except requests.exceptions.ConnectionError:
                raise
            except Exception:
                if retries_remaining <= 0:
                    logger.error('JSON request failed for %s',
                                 path,
                                 exc_info=True)
                    raise

                # ten minutes with some noise
                sleep_seconds = average_delay + Random().uniform(-10, 10)
                logger.warning(
                    'JSON request failed. Sleeping for %ss before retry.',
                    sleep_seconds,
                    exc_info=True)
                time.sleep(sleep_seconds)
                retries_remaining -= 1
                average_delay += 600

    def _retry_json(self, method, path, data=None, params=None, retries: int = 3) -> RequestValue:
        r = self._retry_response(method, path, data=data, params=params, retries=retries)
        return (r.status_code, r.json())

    def patch_json(self, path: str, data: typing.Any, params=None, retries: int = 3) -> RequestValue:
        return self._retry_json(self.patch, path, data=data, params=params, retries=retries)

    def post_json(self, path: str, data: typing.Any, retries: int = 3) -> RequestValue:
        """ Post a JSON object to the web server, and return a JSON object.

        Args:
           path: the relative path to add to the qai_path used in login()
           data: a JSON object that will be converted to a JSON string
           retries: the number of times to retry the request before failing.
        Returns:
           The HTML status code with the response body, converted from JSON.
        """
        return self._retry_json(self.post, path, data=data, retries=retries)

    def generate_receive_url(self, locid: typing.Optional[int], rfidlst: typing.List[str]) -> str:
        """Generate the URL in string form that can be used to add new chemical stock
        items to QAI.

        Note that this call does not actually perform an API call to QAI (this is done
        on the webclient). This routine simply determines the URL string required.

        Args:
           locid: the id of the location at which the new items are to be added.
           rfidlst: a non-empty list of RFID label strings (typically of the form 'CHEMxxxxx')
              that are to be added.
        Returns:
           a string containing the required to add these RFID's to QAI.
        """
        if rfidlst is None or len(rfidlst) == 0:
            raise RuntimeError("Empty rfidlst")
        ustr = self.qai_path + PATH_REAGENT_RECEIVE + '?'
        arglst = []
        if locid is not None:
            arglst.append("location_id={}".format(locid))
        arglst.append("rfids=" + ",".join(["{}".format(rfid) for rfid in rfidlst]))
        return ustr + "&".join(arglst)

    def _rawget(self, path: str, params: dict = None, retries: int = 3) -> requests.Response:
        """Perform a get call to the server, in which we do NOT expect a json response
        from the server.
        """
        return self._retry_response(self.get,
                                    path,
                                    params=params,
                                    retries=retries,
                                    expect_json=False)

    def get_json(self, path: str, params: dict = None, retries=3) -> RequestValue:
        """Retrieve a JSON object from the web server using a http GET call.
        Args:
           path: the relative path to add to settings.qai_path.
           params: URL parameters to be added to the URL.
           retries: the number of times to retry the request before failing.
        Returns:
           The HTML response body, parsed as a JSON object.
        """
        return self._retry_json(self.get, path, params=params, retries=retries)

    def delete_json(self, path: str, params: dict = None, retries=3) -> RequestValue:
        """Make a HTTP delete call
        Args:
           path: the relative path to add to settings.qai_path.
           params: URL parameters to be added to the URL.
           retries: the number of times to retry the request before failing.
        Returns:
           The HTML response body, parsed as a JSON object.
        """
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
# changed 2018-09-10: PATH_REAGENT_LIST_SUPPLIERS = '/qcs_reagent/list_suppliers'
PATH_REAGENT_LIST_SUPPLIERS = '/qcs_supplier_companies'

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
    def __init__(self, qaidct: typing.Optional[QAIdct],
                 tsdct: QAIChangedct) -> None:
        self._qaidct = qaidct or QAISession.get_empty_QAIdct()
        self._tsdct = tsdct

    def get_data(self) -> QAIdct:
        return self._qaidct

    def get_timestamp(self) -> QAIChangedct:
        return self._tsdct


class QAISession(Session):
    """A requests session with some QAI-API-specific functions added."""

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

    @classmethod
    def get_empty_QAIdct(cls) -> QAIdct:
        return dict([(k, None) for k in cls.qai_key_lst])

    def _get_location_list(self) -> typing.List[dict]:
        """Retrieve a list of all locations stored in the QAI database.
        Returns:
           The dicts in the list contain two keys: 'id' and 'name'.
        Raises:
           RuntimeError: if the response code from the QAI server is not HTTP_OK.
        """
        rcode, loclst = self.get_json(PATH_LOCATION_LIST)
        if rcode != HTTP_OK:
            raise RuntimeError("call for location_list failed")
        return loclst

    def _get_supplier_list(self) -> typing.List[str]:
        """Retrieve a list of reagent suppliers as a list of strings.
        Returns:
           A list of strings.
        Raises:
           RuntimeError: if the response code from the QAI server is not HTTP_OK.
        """
        rcode, supplierlst = self.get_json(PATH_REAGENT_LIST_SUPPLIERS)
        if rcode != HTTP_OK:
            raise RuntimeError("call for supplier_list failed")
        return supplierlst

    def _get_reagent_list(self) -> typing.List[dict]:
        """Retrieve a list of all reagents.
        Returns:
           The dicts contain two keys: 'id' and 'name'.
        Raises:
           RuntimeError: if the response code from the QAI server is not HTTP_OK.
        """
        rcode, reagent_lst = self.get_json(PATH_REAGENT_LIST_REAGENTS)
        if rcode != HTTP_OK:
            raise RuntimeError("call for reagent_lst failed")
        return reagent_lst

    def _get_reagent_items(self, reagent_lst: typing.List[dict]) -> typing.Dict[int, dict]:
        """Retrieve the reagent items for each reagent dict provided.
        Args:
           reagent_lst: a list of reagent dicts.
        Returns:
           Return a top-level dict with the reagent_id as a key.
           The value of the top-level dict is a dict resulting
           from the show API call. (I.e. the reagent_item_lst,  a list in "items", e.g.:
           reag_dct = get_reagent_items(rlst)
           my_reag_item_lst = reag_dct[my_reagent_id]['items']
        Raises:
           RuntimeError: if the response code from the QAI server is not HTTP_OK.
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

        Returns:
           A dict in which the keys are defined as class variables in :class:`QAISession`.
           The values are strings representing time stamps.
        Raises:
           RuntimeError: if the response code from the QAI server is not HTTP_OK.
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

        This routine attempts to download the complete data set from QAI, regardless
        of the data stored locally.

        Returns:
           The retrieved QAIDataset.
        Raises:
           RuntimeError: if the response code from the QAI server is not HTTP_OK.
        """
        rdct: QAIdct = {}
        for k, url in self.data_url_lst:
            try:
                rcode, rval = self.get_json(url)
            except json.decoder.JSONDecodeError:
                raise RuntimeError("JSON error on {}".format(url))
            if rcode != HTTP_OK:
                raise RuntimeError("call for {} ({}) failed".format(k, url))
            rdct[k] = rval
        tsdct = self.get_QAI_ChangeData()
        return QAIDataset(rdct, tsdct)

    def clever_update_QAI_dump(self, qaiDS: QAIDataset) -> QAIUpdatedct:
        """Update only those parts of the QAI dataset that are out of date.

        For every QAI database table stored locally, we store in addition
        a timestamp received from the QAI server at the time of data retrieval.
        We query the QAI server for its current timestamp values, and then,
        by comparison, only update those entries in qaiDS from the server
        that are out of date.
        The timestamps stored in qaiDS are also updated as necessary.

        Args:
           qaiDS: the qai dataset to be updated if necessary.

        Returns:
           Return a dictionary with identical keys to qaiDS (i.e. the names of
           the database tables).
           The values of the dict are
           a boolean := "an update from the server occurred"

        Raises:
           RuntimeError: if the response code from the QAI server is not HTTP_OK.
        """
        tsdct = qaiDS.get_timestamp()
        qaidct = qaiDS.get_data()
        for dctname, tdct in [("tsdct", tsdct), ("qaidct", qaidct)]:
            if set(tdct.keys()) != self.qai_key_set:
                raise RuntimeError("dct {} has wonky keys {}".format(dctname, tdct.keys()))
        newtsdct = self.get_QAI_ChangeData()
        retdct: QAIUpdatedct = {}
        for k, dataurl in self.data_url_lst:
            new_timestamp = newtsdct[k]
            do_update = retdct[k] = new_timestamp != tsdct[k]
            if do_update:
                # we need to update from the server
                logger.debug('getting {} from QAI {}'.format(k, dataurl))
                rcode, rval = self.get_json(dataurl)
                if rcode != HTTP_OK:
                    raise RuntimeError("call for {} ({}) failed".format(k, dataurl))
                qaidct[k] = rval
                tsdct[k] = new_timestamp
            else:
                logger.debug('skipping QAi {} url {}'.format(k, dataurl))
        return retdct
