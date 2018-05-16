
# A module to access the QAI system via the requests library

import typing

import requests
import requests.exceptions
import json
import serverlib.timelib as timelib
import serverlib.serverconfig as serverconfig
import serverlib.yamlutil as yamlutil


def tojson(data) -> str:
    """Convert the data structure to json.
    see https://docs.python.org/3.4/library/json.html
    """
    try:
        retstr = json.dumps(data, separators=(',', ':'), default=str)
    except TypeError as e:
        print("problem converting to json '{}'".format(data))
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


def raw_get_json_data(url: str) -> typing.Any:
    """Perform a http request to the provided url.
    Convert the returned json string into a python data structure
    which we return."""
    try:
        r = requests.get(url)
    except requests.exceptions.ConnectionError as e:
        return None
    return fromjson(r.content)


QAI_dct = typing.Dict[str, typing.Any]

StockItem_dct = typing.Dict[str, typing.Any]

Location_dct = typing.Dict[str, typing.List[StockItem_dct]]


def rawdata_to_qaidct(mydat: typing.Any) -> QAI_dct:
    return {"utc_time": timelib.utc_nowtime(), "data": mydat}


def get_json_data_with_time(url: str) -> typing.Optional[QAI_dct]:
    """Perform a http request to the provided url.
    Return a dict containing a time stamp in UTC and the requested data.
    """
    mydat = raw_get_json_data(url)
    if mydat is None:
        return None
    return rawdata_to_qaidct(mydat)


STATE_DIR_ENV_NAME = serverconfig.STATE_DIR_ENV_NAME


class BaseQAIdata:
    def __init__(self, qaiurl: str, locQAIfname: str) -> None:
        """qaiurl: the URL to access in order to get current stock information.
        This information is stored to a local file locQAIfname in the server state
        directory with a time stamp."""
        self._qaiurl = qaiurl
        self._locQAIfname = locQAIfname
        self._set_cur_data(self.loadfileQAIdata())

    def _set_cur_data(self, qai_dct: typing.Optional[QAI_dct]) -> bool:
        self.cur_data = qai_dct
        self._locdct = self._check_massaga_data()
        return self.cur_data is not None and self._locdct is not None

    def _check_massaga_data(self) -> typing.Optional[Location_dct]:
        """Verify and convert the raw json data read from QAI via the API
        into something that the stocky webclient can digest easily.
        Return the successfully converted location_dict or None.
        """
        dlst = self.cur_data.get('data', None) if self.cur_data is not None else None
        if dlst is None:
            return None
        locdct: Location_dct = {}
        LOC_KEY = 'location'
        for item_dct in dlst:
            if not isinstance(item_dct, dict):
                print("item_dct is not a dict")
                return None
            # We need to know whether the key is present (it must be).
            # The value of the key may be None, in which case we set it to Unknown
            if LOC_KEY in item_dct:
                for loc in BaseQAIdata.splitlocstring(item_dct[LOC_KEY]):
                    locdct.setdefault(loc, []).append(item_dct)
            else:
                print("location is missing in {}".format(item_dct))
                return None
        # if we get this far, we have succeeded
        return locdct

    @staticmethod
    def splitlocstring(locstr: str) -> typing.List[str]:
        """Split a location string into a number of locations"""
        if locstr is None:
            return ['Unknown']
        # try to split according to '/'
        ll = [s.strip() for s in locstr.split('/')]
        if len(ll) > 1:
            return ll
        # try ';'
        ll = [s.strip() for s in locstr.split(';')]
        if len(ll) > 1:
            return ll
        # give up and return the location as is
        return [locstr.strip()]

    def generate_webclient_stocklist(self) -> dict:
        """Generate the stock list in a form required by the web client."""
        # list of all locations
        loc_lst = list(self._locdct.keys()) if self._locdct is not None else []
        loc_lst.sort(key=lambda t: t[0])
        UNKNOWNSTR = 'Unknown'
        if UNKNOWNSTR not in loc_lst:
            loc_lst.append(UNKNOWNSTR)
        # need a dict: locname -> locndx
        ndx_dct = dict([(locname, locndx) for locndx, locname in enumerate(loc_lst)])
        unknown_ndx = ndx_dct[UNKNOWNSTR]
        # make sure locnames are unique
        if len(ndx_dct) != len(loc_lst):
            raise RuntimeError("location names are not unique!")
        help_txt_keys = ["name", "id", "category",
                         "hazards", "scope", "tags", "expiry_time",
                         "storage", "lot_id", "lot_num", "supplier", "catalog_number",
                         "prepared_by", "expected_status",
                         "date_made", "date_in_use", "date_expires", "date_used_up"]
        # stock item list: locndx, itm_str, tagnum, helptext
        stock_itmlst = []
        klst = ('name', 'id')
        dlst = self.cur_data['data'] if self.cur_data is not None else []
        for item_dct in dlst:
            datatup = tuple([item_dct.get(k, "Unknown") for k in klst])
            # prepend location ndx
            locndx = ndx_dct.get(item_dct.get('location', UNKNOWNSTR), unknown_ndx)
            # append helptext that appears when the user hovers the mouse over a specific stock item
            # line in a table
            helptext = "\n ".join(["{}: {}".format(k, item_dct.get(k, "no information")) for k in help_txt_keys])
            dtup = (locndx, *datatup, helptext)
            stock_itmlst.append(dtup)
        # modify loc_lst strings to include number of items at each location
        if self._locdct is not None:
            loc_lst = ["{}: ({})".format(locstr, len(self._locdct[locstr])) for locstr in loc_lst]
        return {'loclist': loc_lst, 'itemlist': stock_itmlst}

    def loadfileQAIdata(self) -> QAI_dct:
        """Attempt to load previously saved QAI data from file.
        Return the data read, or None if this fails."""
        try:
            retval = yamlutil.readyamlfile(self._locQAIfname, STATE_DIR_ENV_NAME)
        except RuntimeError as e:
            retval = None
        return retval

    def dumpfileQAIdata(self) -> None:
        """Save the current QAI data to file for later retrieval."""
        if self.cur_data is None:
            raise RuntimeError("Attempting to dump empty QAI data")
        yamlutil.writeyamlfile(self.cur_data, self._locQAIfname, STATE_DIR_ENV_NAME)

    def qai_is_online(self) -> bool:
        """Return := 'the QAI url can be accessed'
        NOTE: This state could change depending on whether the laptop is plugged in to
        the wired network or not.
        """
        raise NotImplementedError('not implemented')

    def has_qai_data(self) -> bool:
        """Return true iff we have QAI data available.
        """
        return self.cur_data is not None

    def get_qai_downloadtimeUTC(self) -> typing.Optional[timelib.DateTimeType]:
        """Return the UTC datetime record of the time the QAI data was downloaded.
        Return None iff no data is available.
        """
        return self.cur_data.get('utc_time', None) if self.cur_data is not None else None

    def pull_qai_data(self) -> bool:
        """Perform a http request to the QAI server and download the newest version
        from it.
        Return := 'the data pull was successful'
        """
        raise NotImplementedError('not implemented')

    def _loadrawdata(self, fname: str) -> bool:
        """Load raw QAI data from a file into this class structure.
        The load time data is set to the current time."""
        try:
            rawdat = yamlutil.readyamlfile(fname, STATE_DIR_ENV_NAME)
        except RuntimeError as e:
            return False
        return self._set_cur_data(rawdata_to_qaidct(rawdat))

    def _location_summary(self) -> typing.Optional[typing.List[typing.Tuple[str, int]]]:
        """Produce a summary of the stock by location.
        """
        if self._locdct is None:
            return None
        retlst = [(loc_name, len(loc_lst)) for loc_name, loc_lst in self._locdct.items()]
        retlst.sort(key=lambda t: t[0])
        return retlst


class QAIdata(BaseQAIdata):

    def qai_is_online(self) -> bool:
        cur_data = get_json_data_with_time(self._qaiurl)
        return (cur_data is None)

    def pull_qai_data(self) -> bool:
        """Perform a http request to the QAI server and download the newest version
        from it.
        Return := 'the data pull was successful'
        """
        return self._set_cur_data(get_json_data_with_time(self._qaiurl))
