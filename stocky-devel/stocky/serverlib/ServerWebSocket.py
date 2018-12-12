"""Provide a level of abstraction to websockets on the server side to allow for different
encoding and/or compression approaches."""


import typing
# import gevent
from geventwebsocket import websocket
import geventwebsocket.exceptions

import serverlib.qai_helper as qai_helper
from webclient.commonmsg import CommonMSG

WebsocketMSG = typing.Dict[str, typing.Any]

EOF_dct = {"msg": CommonMSG.MSG_WC_EOF, "data": None}


class BaseWebSocket:
    """Encapsulate a raw websocket instance and provide methods for
    encoding/decoding of python objects into/from websocket data streams."""
    def __init__(self, rawws: websocket, logger) -> None:
        """

        Args:
           rawws: the raw websocket instance
           logger: a python logging class
        """
        self.ws = rawws
        self.logger = logger

    def close(self):
        self.ws.close()

    def receiveMSG(self) -> typing.Optional[WebsocketMSG]:
        """Block until a message is received from the websocket channel,

        The raw message received over the websocket is transformed into a python
        object by calling :meth:`decodeMSG` on the received data string first.
        The resulting python object is returned.

        Returns:
           The message read as a python object.
           If an error occurs, a message is logged and None is returned.
        """
        lverb = True
        try:
            if lverb:
                print("self.ws.receive()...")
            rawmsg = self.ws.receive()
            if lverb:
                print("self.ws.received!")
        except geventwebsocket.exceptions.WebSocketError as e:
            mm = "recv except {} : {}".format(self, e)
            print(mm)
            self.logger.debug(mm)
            rawmsg = None
        retdct = self.decodeMSG(rawmsg) if rawmsg is not None else EOF_dct
        if retdct is not None and not isinstance(retdct, dict):
            self.logger.error("expected a single dict in json message , but got '{}'".format(retdct))
            retdct = None
        return retdct

    def sendMSG(self, msg: WebsocketMSG) -> None:
        """Send a message over the websocket connection.

        The message is a python data structure which is encoded into a form
        suitable for transmission over the websocket by calling
        :meth:`encodeMSG` first, then transmitting these results.

        Args:
           msg: the message dict to send.
        """
        self.ws.send(self.encodeMSG(msg))

    def decodeMSG(self, rawmsg: typing.Any) -> typing.Optional[WebsocketMSG]:
        """Given a raw message read from the websocket interface,
        convert this into a python object (a dict) and return it.
        Return None if the conversion somehow fails.

        Note:
           This method must be overridden in subclasses.

        Args:
           rawmsg: the raw message read from the websocket.
        Returns:
           The raw message converted into a python data structure.
           Return None is this somehow fails.

        Raises:
           NotImplementedError: when called.
        """
        raise NotImplementedError("decodeMSG not implemented")

    def encodeMSG(self, msg: WebsocketMSG) -> typing.Any:
        """Encode the input message for transmission over the websocket interface.

        Note:
           This method must be overridden in subclasses.

        Args:
           msg: the message (a python object) to encode for transmission

        Returns:
           the message in encoded form for transmission.

        Raises:
           NotImplementedError: when called.
        """
        raise NotImplementedError("encodeMSG not implemented")


class JSONWebSocket(BaseWebSocket):
    """Communicate over a raw websocket using uncompressed JSON-encoded messages.
    """
    def decodeMSG(self, rawmsg: typing.Any) -> typing.Optional[WebsocketMSG]:
        """Given a raw message read from the websocket interface,
        convert this into a python object (a dict) and return it.
        Return None is this somehow fails.
        Here, the message will be a json encoded string.
        """
        retmsg = qai_helper.safe_fromjson(rawmsg)
        if retmsg is None:
            self.logger.error("malformed json string, got '{}'".format(rawmsg))
        return retmsg

    def encodeMSG(self, msg: WebsocketMSG) -> typing.Any:
        """Encode the input message into a json string for transmission over websocket.
        """
        return qai_helper.tojson(msg)
