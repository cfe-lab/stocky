
# define messages that the webclient and the server have in common
# This module is imported by both python3 on the server and transcrypt on the
# webclient, so must be written accordingly


import typing


# NOTE: naming convention adopted here:
# MSG_WC_*: messages generated by the webclient
# MSG_RF_*: messages generated by the RFID reader
# MSG_SV_*: messages generated by the server

class CommonMSG:
    # the server has produced a random number
    MSG_SV_RAND_NUM = 'RND'
    # the USB device has changed state (presence/absence)
    MSG_SV_USB_STATE_CHANGE = 'USB_STATE'

    # the web client is performing a stock check
    MSG_WC_STOCK_CHECK = 'STOCK_MODE'

    # the web client is searching for a specific item ('radar mode')
    MSG_WC_RADAR_MODE = 'RADAR_MODE'

    # the RFID reader has produced some stock taking data
    MSG_RF_STOCK_DATA = 'STOCK_DATA'

    # the RFID reader has produced some radar data
    MSG_RF_RADAR_DATA = 'RADAR_DATA'

    # the RFID reader has produced a command response
    MSG_RF_CMD_RESP = 'RF_CMD_RESP'

    # the RFID 
    def __init__(self, msg: str, data: typing.Any) -> None:
        self.msg = msg
        self.data = data

    def as_dict(self) -> dict:
        return dict(msg=self.msg, data=self.data)
