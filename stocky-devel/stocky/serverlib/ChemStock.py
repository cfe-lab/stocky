
# A module to access the QAI system via the requests library

# import typing

# import requests
# import requests.exceptions
import logging
# import serverlib.timelib as timelib
# import serverlib.serverconfig as serverconfig
# import serverlib.yamlutil as yamlutil
import serverlib.qai_helper as qai_helper

logger = logging.Logger('ChemStock')


class ChemStock:
    def __init__(self, qaiurl: str,
                 uname: str,
                 passwd: str,
                 locQAIfname: str) -> None:
        """qaiurl: the URL to access in order to get current stock information from QAI.
        uname, passwd: required to authenticate against the QAI system.
        This stock information is stored to a local file locQAIfname in the
        server state directory with a time stamp."""
        self._qaiurl = qaiurl
        self._locQAIfname = locQAIfname
        self._set_cur_data(self.loadfileQAIdata())
        self._uname = uname
        self.s = qai_helper.Session()
        try:
            self.s.login(qaiurl, uname, passwd)
        except RuntimeError as e:
            logger.error("login failed as user '{}': {}".format(uname, e))

    def qai_is_online(self) -> bool:
        """Return := 'the QAI url can be accessed'
        NOTE: This state could change depending on whether the laptop is plugged in to
        the wired network or not.
        """
        return self.s.is_logged_in()

    def refresh_QAI_data(self) -> bool:
        """Attempt to refresh the QAI reagent tracker information from the server.
        Return := 'the QAI could be accessed and the update succeeded.
        """
        if not self.qai_is_online():
            return False
