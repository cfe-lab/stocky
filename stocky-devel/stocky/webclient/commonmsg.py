
# define messages that the webclient and the server have in common
# This module is imported by both python3 on the server and transcrypt on the
# webclient, so must be written accordingly


import typing


class CommonMSG:
    # the server has produced a random number
    MSG_RAND_NUM = 'RND'
    # the USB device has changed state (presence/absence)
    MSG_USB_STATE_CHANGE = 'USB_STATE'

    # the web client is performing a stock check
    MSG_WC_STOCK_CHECK = 'STOCK'

    # the web client is searching for a specific item ('radar mode')
    MSG_WC_RADAR_MODE = 'RADAR'

    def __init__(self, msg: str, data: typing.Any) -> None:
        self.msg = msg
        self.data = data

    def as_dict(self) -> dict:
        return dict(msg=self.msg, data=self.data)
