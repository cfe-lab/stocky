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
    """Encapsulate a raw websocket instance and provided methods for encoding/decoding
    of messages."""
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
        retdct = self._decodeMSG(rawmsg) if rawmsg is not None else EOF_dct
        if retdct is not None and not isinstance(retdct, dict):
            self.logger.error("expected a single dict in json message , but got '{}'".format(retdct))
            retdct = None
        return retdct

    def sendMSG(self, msg: WebsocketMSG) -> None:
        """Send the message over the websocket connection.
        Args:
           msg: the message dict to send.
        """
        self.ws.send(self._encodeMSG(msg))

    def _decodeMSG(self, rawmsg: typing.Any) -> typing.Optional[WebsocketMSG]:
        """Given a raw message read from the websocket interface,
        convert this into a python object (a dict) and return it.
        This method must be overriden in subclasses.
        Args:
           rawmsg: the raw message read from the websocket.
        Returns:
           The raw message converted into a python data structure.
           Return None is this somehow fails.

        Raises:
           NotImplementedError: when called.
        """
        raise NotImplementedError("decodeMSG not implemented")

    def _encodeMSG(self, msg: WebsocketMSG) -> typing.Any:
        """Encode the input message for transmission over the websocket interface."""
        raise NotImplementedError("encodeMSG not implemented")


class JSONWebSocket(BaseWebSocket):
    """Communicate over a raw websocket using uncompressed JSON-encoded messages.
    """
    def _decodeMSG(self, rawmsg: typing.Any) -> typing.Optional[WebsocketMSG]:
        """Given a raw message read from the websocket interface,
        convert this into a python object (a dict) and return it.
        Return None is this somehow fails.
        """
        retmsg = qai_helper.safe_fromjson(rawmsg)
        if retmsg is None:
            self.logger.error("malformed json string, got '{}'".format(rawmsg))
        return retmsg

    def _encodeMSG(self, msg: WebsocketMSG) -> typing.Any:
        """Encode the input message for transmission over the websocket interface."""
        return qai_helper.tojson(msg)
