# handle QAI authentication logic

import typing

from org.transcrypt.stubs.browser import window

thewin = None


def thefunk():
    print("THEFUNK")
    if thewin is not None:
        all_cookies = thewin.document.cookie
        print("GOT cookies {}".format(all_cookies))


class qaiauth:
    def __init__(self, qaiurl: str) -> None:
        self.qaiurl = qaiurl
        self.islogged_in = False
        self.win = None
        self._my_cookie = None

    def is_logged_in(self) -> bool:
        """Return 'user is logged in'"""
        pass

    
    def get_auth_cookie(self) -> typing.Optional[str]:
        """Provide User authentication to QAI.
        Return None if this failed.
        """
        self.check_for_cookie()
        return self._my_cookie

    def check_for_cookie(self):
        if self.win is None:
            # redirect and allow user to log in.
            print("redirect...{}".format(self.qaiurl))
            self.win = window.open(self.qaiurl)
            self.win.onload = thefunk
        global thewin
        thewin = self.win
        #
        all_cookies = self.win.document.cookie
        print("GOT cookies {}".format(all_cookies))
        # print("GOT cookies")
        self._my_cookie = all_cookies
