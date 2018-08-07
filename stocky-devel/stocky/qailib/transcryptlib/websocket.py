# provide a low-level pythonic interface to the client side WebSockets

import typing
from org.transcrypt.stubs.browser import WebSocket,\
    __new__, __pragma__, JSON


class BaseRawWebSocket:
    def __init__(self) -> None:
        print("RAW open")
        self._isopen = False
        self._cbhandler = None

    def send_raw(self, data_to_server) -> None:
        raise NotImplementedError('send_raw not implemented')

    def is_open(self):
        return self._isopen

    def send(self, data_to_server) -> None:
        self.send_raw(data_to_server)

    def close(self) -> None:
        self._ws.close()

    def set_CB_handler(self, cb_handler) -> None:
        self._cbhandler = cb_handler

    def on_open_cb(self, event) -> None:
        print('on_open_cb')
        if self._cbhandler is not None:
            self._cbhandler.on_open_cb(event)

    def on_error_cb(self, event) -> None:
        print('on_error_cb')
        if self._cbhandler is not None:
            self._cbhandler.on_error_cb(event)

    def on_message_cb(self, event) -> None:
        print('on_message_cb')
        if self._cbhandler is not None:
            self._cbhandler.on_message_cb(event)


class RawWebsocket(BaseRawWebSocket):
    """A websocket that sends raw data to and fro without any data conversion.
    This is a thin python interface to the underlying Javascript API for websockets
    on the client side.
    See https://developer.mozilla.org/en/docs/Web/API/WebSocket for complete documentation
    of the websocket API.
    """

    def __init__(self, url: str, protocol_lst: list) -> None:
        """Initialise a raw web socket. The url is the name of the server to connect to.
        The protocol_lst is either a string or a list of strings.
        An empty list may be provided.
        """
        BaseRawWebSocket.__init__(self)
        self._ws = __new__(WebSocket(url, 'json'))
        # self._ws = __new__(WebSocket(url))
        # self._ws = __new__(WebSocket(url, protocol_lst))
        __pragma__(
            'js', '{}',
            'self._ws.onopen = function(event){self._isopen = true; self.on_open_cb(event);}'
        )
        __pragma__(
            'js', '{}',
            'self._ws.onerror = function(event){self.on_error_cb(event);}')
        __pragma__(
            'js', '{}',
            'self._ws.onmessage = function(event){self.on_message_cb(event);}')

    def close(self) -> None:
        self._ws.close()

    def send_raw(self, data_to_server) -> None:
        if self._isopen:
            self._ws.send(data_to_server)
        else:
            print('NOT sending (isopen=False)....', data_to_server)


class CNVWebsocket:
    """A websocket that converts to/from websocket data..."""

    def __init__(self, rawws: BaseRawWebSocket) -> None:
        self._rawws = rawws
        rawws.set_CB_handler(self)

    def send(self, data_to_server) -> None:
        """Convert the data structure to JSON before sending it
        to the server."""
        print("CNVWebsocket.send {}".format(data_to_server))
        self._rawws.send_raw(self.encode(data_to_server))

    def is_open(self):
        return self._rawws.is_open()

    def on_message_JSON(self, data) -> None:
        """This method will be called whenever a message is received from the server.
        The data from the server will be provided in a javascript data structure.
        """
        raise NotImplementedError('on_message_JSON not implemented')

    def on_message_cb(self, event) -> None:
        datain = self.decode(event.data)
        self.on_message_JSON(datain)

    def encode(self, data_to_server) -> typing.Any:
        """encode the data from transfer..."""
        raise NotImplementedError('encode not implemented')

    def decode(self, data_from_server) -> typing.Any:
        """Decode data from the server"""
        raise NotImplementedError('decode not implemented')


class JSONWebsocket(CNVWebsocket):
    """A websocket that converts all data to JSON before sending it to the server.
    It also expects the data from the server to be in JSON format, and converts this
    data before passing it to the client via the on_message_JSON method.
    """

    def encode(self, data_to_server) -> typing.Any:
        """encode the data from transfer..."""
        return JSON.stringify(data_to_server)

    def decode(self, data_from_server) -> typing.Any:
        """Decode data from the server"""
        return JSON.parse(data_from_server)


class BLAWebsocket(CNVWebsocket):
    """A websocket that converts all data to MessagePack before sending it to the server.
    It also expects the data from the server to be in MessagePack format, and converts this
    data before passing it to the client via the on_message_JSON method.
    """

    def encode(self, data_to_server) -> typing.Any:
        """encode the data from transfer..."""
        # return JSON.stringify(data_to_server)
        # return msgpack.encode(data_to_server)
        pass

    def decode(self, data_from_server) -> typing.Any:
        """Decode data from the server"""
        # return JSON.parse(data_from_server)
        # retval = msgpack.decode(data_from_server)
        # print("MPACK decode says {}  and {}".format(data_from_server, retval))
        # return retval
        pass
