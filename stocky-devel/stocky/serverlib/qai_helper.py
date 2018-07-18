import json
import logging
from random import Random
import requests
import time
import typing

logger = logging.getLogger('qai_helper')


StatusCode = int

RequestValue = typing.Tuple[StatusCode, typing.Any]


class Session(requests.Session):

    def __init__(self) -> None:
        super().__init__()
        self._islogged_in = False

    def login(self, qai_path: str, qai_user: str, password: str) -> None:
        """ Login to QAI before calling post_json or get_json.

        @raise RuntimeError: when the QAI server rejects the user and password.
        """
        self.qai_path = qai_path
        response = self.post(qai_path + "/account/login",
                             data={'user_login': qai_user,
                                   'user_password': password})
        if response.status_code == requests.codes.forbidden:  # @UndefinedVariable
            raise RuntimeError("Login failed for QAI user '{}'.".format(qai_user))
        self._islogged_in = True

    def is_logged_in(self):
        return self._islogged_in

    def _retry_response(self,
                        method,
                        path: str,
                        data: typing.Any=None,
                        params: dict=None,
                        retries: int=3) ->requests.Response:
        if not self._islogged_in:
            raise RuntimeError("Must log in before using the call API")
        json_data = data and json.dumps(data)
        headers = {'Accept': 'application/json'}
        if json_data:
            headers['Content-Type'] = 'application/json'
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

    def _scoget(self, path: str, params: dict=None, retries=3) -> requests.Response:
        return self._retry_response(self.get, path, params=params, retries=retries)

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

HTTP_OK = requests.codes.ok
HTTP_CREATED = requests.codes.created


QAIdct = typing.Dict[str, typing.Any]


class QAISession(Session):
    """Add some QAI- API-specific functions"""

    # these are entries in the QAIdct
    QAIDCT_REAGENTS = 'reagents'
    QAIDCT_REAGENT_ITEMS = 'reagent_items'
    QAIDCT_REAITEM_STATUS = 'reagent_item_status'
    QAIDCT_REAITEM_COMPOSITION = 'reagen_item_composition'
    QAIDCT_LOCATIONS = 'locations'
    QAIDCT_USERS = 'users'

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

    def get_QAI_dump(self) -> QAIdct:
        """Retrieve the complete reagent database as a dict.

        """
        rdct = {}
        for k, url in [(QAISession.QAIDCT_REAGENTS, DUMP_REAGENTS),
                       (QAISession.QAIDCT_REAGENT_ITEMS, DUMP_REAG_ITEMS),
                       (QAISession.QAIDCT_REAITEM_STATUS, DUMP_REAG_ITEM_STATUS),
                       (QAISession.QAIDCT_REAITEM_COMPOSITION, DUMP_REAG_ITEM_COMPOSITION),
                       (QAISession.QAIDCT_LOCATIONS, DUMP_LOCATION),
                       (QAISession.QAIDCT_USERS, PATH_USER_LIST)]:
            rcode, rval = self.get_json(url)
            if rcode != HTTP_OK:
                raise RuntimeError("call for {} ({}) failed".format(k, url))
            rdct[k] = rval
        return rdct
