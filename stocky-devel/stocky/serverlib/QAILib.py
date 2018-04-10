
# A module to access the QAI system via the requests library

import typing

import datetime as dt

import requests
import requests.exceptions
import json
import serverlib.serverconfig as serverconfig
import serverlib.yamlutil as yamlutil


def tojson(data) -> str:
    """Convert the data structure to json.
    see https://docs.python.org/3.4/library/json.html
    """
    return json.dumps(data, separators=(',', ':'))


def fromjson(data_bytes: bytes) -> typing.Any:
    """Convert bytes into a data struct which we return."""
    return json.loads(data_bytes)


def raw_get_json_data(url: str) -> typing.Any:
    """Perform a http request to the provided url.
    Convert the returned json string into a python data structure
    which we return."""
    try:
        r = requests.get(url)
    except requests.exceptions.ConnectionError as e:
        return None
    return fromjson(r.content)


QAI_dict = typing.Dict[str, typing.Any]


def get_json_data_with_time(url: str) -> QAI_dict:
    """Perform a http request to the provided url.
    Return a dict containing a time stamp in UTC and the requested data.
    """
    mydat = raw_get_json_data(url)
    if mydat is None:
        return None
    return {"utc_time": dt.datetime.now(), "data": mydat}


STATE_DIR_ENV_NAME = serverconfig.STATE_DIR_ENV_NAME


class BaseQAIdata:
    def __init__(self, qaiurl: str, locQAIfname: str) -> None:
        """qaiurl: the URL to access in order to get current stock information.
        This information is stored to a local file locQAIfname in the server state
        directory with a time stamp."""
        self._qaiurl = qaiurl
        self._locQAIfname = locQAIfname
        self.cur_data: QAI_dict = self.loadQAIdata()

    def loadQAIdata(self) -> QAI_dict:
        try:
            retval = yamlutil.readyamlfile(self._locQAIfname, STATE_DIR_ENV_NAME)
        except RuntimeError as e:
            return None
        return retval

    def qai_is_online(self) -> bool:
        """Return := 'the QAI url can be accessed'
        NOTE: This state could change depending on whether the laptop is plugged in to
        the wired network or not.
        """
        raise NotImplementedError('not implemented')

    def has_qai_data(self) -> bool:
        """Return true iff we have QAI data available.
        """
        raise NotImplementedError('not implemented')

    def pull_qai_data(self) -> bool:
        """Perform a http request to the QAI server and download the newest version
        from it.
        Return := 'the data pull was successful'
        """
        raise NotImplementedError('not implemented')


class QAIdata(BaseQAIdata):

    def qai_is_online(self) -> bool:
        cur_data = get_json_data_with_time(self._qaiurl)
        return (cur_data is None)

    def pull_qai_data(self) -> bool:
        """Perform a http request to the QAI server and download the newest version
        from it.
        """
        cur_data = get_json_data_with_time(self._qaiurl)
        if cur_data is None:
            return False
        self._cur_data = cur_data
        yamlutil.writeyamlfile(cur_data, self._locQAIfname, STATE_DIR_ENV_NAME)
        return True

