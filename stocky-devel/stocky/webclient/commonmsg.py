"""Define messages that the webclient and the server have in common.
The CommonMSG class forms the basis of communication over websockets
between server and webclient as well as between the server and software layers
controlling the RFID reader.

Essentially, all three parties (server, webclient and rfid reader) communicate
with each other via CommonMSG instances that are put onto a queue that the
controller class of the server reacts to.

Note:
   This module is imported by both python3 on the server and transcrypt on the
   webclient, so must be written accordingly.
"""

import typing


class CommonMSG:
    """The message class that both stocky server and webclient use to communicate
    to each over websocket with.

    Note:
    The naming convention adopted for the message types is:
      * MSG_WC_*: messages generated by the webclient
      * MSG_RF_*: messages generated by the RFID reader
      * MSG_SV_*: messages generated by the server

    This is important to adhere to, as this is how :py:meth:`is_from_server`,
    :py:meth:`is_from_webclient` and :py:meth:`is_from_rfid_reader` are implemented.
    """

    # the server has produced a random number
    MSG_SV_RAND_NUM = 'SV_RND'

    # the server has produced a timer event
    MSG_SV_TIMER_TICK = 'SV_TIMER'

    # the server is sending a list of all stock locations
    # in response to a MSG_WC_STOCK_CHECK
    # MSG_SV_NEW_STOCK_LIST = 'SV_NEW_STOCK_LIST'
    # the web client is performing a stock check
    # -- server should send a list of all locations with MSG_SV_STOCK_LOCATIONS
    # MSG_WC_STOCK_CHECK = 'WC_STOCK_MODE'

    # the server wants to send a generic command directly to the RFID reader
    MSG_SV_GENERIC_COMMAND = 'SV_GENERIC_CMD'

    # the web client is sending uname, password info so
    # that the stocky server can try to authenticate
    MSG_WC_LOGIN_TRY = 'WC_LOGIN_TRY'

    # the server is providing the result of a login attempt sent by MSG_WC_LOGIN_TRY
    MSG_SV_LOGIN_RES = 'SV_LOGIN_RES'

    # the web client wants to log out.
    MSG_WC_LOGOUT_TRY = "WC_LOGOUT_TRY"
    # the server acknowledges the logout.
    MSG_SV_LOGOUT_RES = "SV_LOGOUT_RES"

    # ---server RFID reader realted actions
    # the device used to communicate with the RFID scanner has changed state (presence/absence)
    # This is used to signal that the RFID scanner device has come online/ gone offline.
    MSG_SV_FILE_STATE_CHANGE = 'SV_FILE_STATE'

    # the server is setting the RFID scanner in stock check mode
    # MSG_SV_STOCK_CHECK_MODE = 'SV_STOCK_CHECK_MODE'

    # the server is telling the webclient about the status of the RFID reader
    MSG_SV_RFID_STATREP = "SV_RFID_STATREP"

    # state of the RFID communication.
    # these are data values used when reporting MSG_SV_RFID_STATREP
    RFID_OFF = 0
    RFID_ON = 1
    RFID_TIMEOUT = 2

    # there has been some signal from the RFID reader (trigger has been pressed)
    # this message will include on/off data
    MSG_SV_RFID_ACTIVITY = "SV_RFID_ACTIVITY"

    # the webclient is sending some RFID tags to enter to the stock database
    MSG_WC_ADD_STOCK_REQ = 'WC_ADD_STOCK_REQ'
    # the server is sending the URL to add these RFID tags back to the client.
    MSG_SV_ADD_STOCK_RESP = 'SV_ADD_STOCK_RESP'

    # --end of RFID reader related commands.

    # the web client websocket connection has terminated.
    # this message is generated on the server side when the websocket connection
    # to the weblient is terminated. This can happen, e.g. on a page reload on the browser.
    MSG_WC_EOF = 'WC_EOF'

    # the web client has set a stock checking location
    MSG_WC_SET_STOCK_LOCATION = 'WC_STOCK_SET_LOC'

    # the web client is searching for a specific item ('radar mode')
    MSG_WC_RADAR_MODE = 'WC_RADAR_MODE'

    # the server is sending chemstock 'last update' info
    MSG_SV_STOCK_INFO_RESP = 'SV_CS_INFO_RESP'

    # the web client wants the server to send chemstock 'last update' info
    # optionally, the webclient can also tell the server to update the chemstock
    # info from QAI.
    MSG_WC_STOCK_INFO_REQ = 'WC_CS_INFO_REQ'

    # The web client is sending the server some stock location change data.
    # This data is produced in the course of the stock taking procedure, i.e.,
    # which RFID tags were detected at a particular location.
    MSG_WC_LOCATION_INFO = 'WC_LOCATION_INFO'

    # When reviewing location mutation list, wc will request all location changes
    # this data will be provided by the stocky server.
    MSG_WC_LOCMUT_REQ = 'WC_LOCMUT_REQ'
    MSG_SV_LOCMUT_RESP = 'SV_LOCMUT_RESP'

    # the RFID reader has produced some radar data
    MSG_RF_RADAR_DATA = 'RF_RADAR_DATA'

    # the RFID reader has produced a command response
    MSG_RF_CMD_RESP = 'RF_CMD_RESP'

    # the server is sending some stocky server configuration data to the webclient
    MSG_SV_SRV_CONFIG_DATA = "SV_CONFIG_DATA"

    # total number of messages: just for cross checking.
    NUM_MSG = 23

    @classmethod
    def _init_class(cls):
        # NOTE: because of transcrypt, we cannot use a set..
        # nor can we seem to be able to define these as class variables.
        # instead, use a class method which is called upon import of the module.
        # Note that, because of this unorthodox way of initialising class variables,
        # mypy gets confused, and believes that the class does not
        # have a valid_msg_lst attribute
        cls.valid_msg_lst = [cls.MSG_SV_RAND_NUM, cls.MSG_SV_TIMER_TICK,
                             cls.MSG_SV_GENERIC_COMMAND,
                             cls.MSG_WC_LOGIN_TRY, cls.MSG_SV_LOGIN_RES,
                             cls.MSG_WC_LOGOUT_TRY, cls.MSG_SV_LOGOUT_RES,
                             cls.MSG_SV_FILE_STATE_CHANGE,
                             cls.MSG_SV_RFID_STATREP, cls.MSG_SV_RFID_ACTIVITY,
                             cls.MSG_WC_ADD_STOCK_REQ, cls.MSG_SV_ADD_STOCK_RESP,
                             cls.MSG_WC_EOF, cls.MSG_WC_SET_STOCK_LOCATION,
                             cls.MSG_WC_RADAR_MODE,
                             cls.MSG_WC_STOCK_INFO_REQ,
                             cls.MSG_SV_STOCK_INFO_RESP,
                             cls.MSG_WC_LOCATION_INFO,
                             cls.MSG_WC_LOCMUT_REQ, cls.MSG_SV_LOCMUT_RESP,
                             cls.MSG_RF_RADAR_DATA,
                             cls.MSG_RF_CMD_RESP,
                             cls.MSG_SV_SRV_CONFIG_DATA
                             ]
        # cls.MSG_WC_STOCK_CHECK,cls.MSG_SV_NEW_STOCK_LIST
        # , cls.MSG_RF_STOCK_DATA
        cls.valid_msg_dct = dict([(k, 1) for k in cls.valid_msg_lst])
        if len(cls.valid_msg_lst) != len(cls.valid_msg_dct):
            raise RuntimeError("Whacky commonmsg._init_class")

    def __init__(self, msg: str, data: typing.Any) -> None:
        """Define a commonmsg class.

        Args:
           msg: one of the predefined message strings
           data: the payload of the message. i.e. a piece of accompanying data
              containing the message content. This
              is often a dict containing further data structures.

        Note:
           data must contain only serialisable data structures for transmission over
           a communication channel such as a websocket. This property is not checked
           for in this class.
        """
        if not isinstance(msg, str):
            raise TypeError('msg must be a string!')
        if CommonMSG.valid_msg_dct.get(msg, None) is None:
            raise ValueError("illegal msg string '{}'".format(msg))
        self.msg = msg
        self.data = data

    def as_dict(self) -> dict:
        """Return this class as a dict for transmission over a communication channel.

        Returns:
           The dict representation of the message.

        Note:
           Under transcrypt, there might be a spurious  '__kwargtrans__' in the dict.
           This can be safely ignored.
        """
        d = dict(msg=self.msg, data=self.data)
        # if '__kwargtrans__' in d:
        #    del d['__kwargtrans__']
        return d

    def __str__(self) -> str:
        return "CommonMSG({}, {})".format(self.msg, self.data)

    def is_from_server(self) -> bool:
        """Determine origin of the message.

        Returns:
           True iff the message was generated by the stocky server.
        """
        return self.msg.startswith('SV_')

    def is_from_webclient(self) -> bool:
        """Determine origin of the message.

        Returns:
           True iff the message was generated by the web client.
        """
        return self.msg.startswith('WC_')

    def is_from_rfid_reader(self) -> bool:
        """Determine origin of the message.

        Returns:
           True iff the message was generated by the RFID reader.
        """
        return self.msg.startswith('RF_')


CommonMSG._init_class()
