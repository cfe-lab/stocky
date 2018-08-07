
# Provide a level of abstraction to websockets on the server side to allow for different
# encoding and/or compression approaches.


import typing
from geventwebsocket import websocket
import geventwebsocket.exceptions

import serverlib.qai_helper as qai_helper

WebsocketMSG = typing.Dict[str, typing.Any]


class BaseWebSocket:
    def __init__(self, rawws: websocket, logger) -> None:
        self.ws = rawws
        self.logger = logger

    def receiveMSG(self) -> typing.Optional[WebsocketMSG]:
        """Block until a message is received from the websocket channel,
        Then return the message read as a python object.
        If an error occurs, this message could be None.
        """
        try:
            rawmsg = self.ws.receive()
        except geventwebsocket.exceptions.WebSocketError as e:
            self.logger.debug("server received a None: {}".format(e))
            rawmsg = None
        if rawmsg is None:
            return None
        retdct = self._decodeMSG(rawmsg)
        if retdct is not None and not isinstance(retdct, dict):
            self.logger.error("expected a single dict in json message , but got '{}'".format(retdct))
            retdct = None
        return retdct

    def sendMSG(self, msg: WebsocketMSG) -> None:
        """Send the message over the websocket connection"""
        self.ws.send(self._encodeMSG(msg))

    def _decodeMSG(self, rawmsg: typing.Any) -> typing.Optional[WebsocketMSG]:
        """Given a raw message read from the websocket interface,
        convert this into a python object (a dict) and return it.
        Return None is this somehow fails.
        """
        raise NotImplementedError("decodeMSG not implemented")

    def _encodeMSG(self, msg: WebsocketMSG) -> typing.Any:
        """Encode the input message for transmission over the websocket interface."""
        raise NotImplementedError("encodeMSG not implemented")


class JSONWebSocket(BaseWebSocket):

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
