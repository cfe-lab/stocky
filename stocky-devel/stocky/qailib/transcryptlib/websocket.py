# provide a low-level pythonic interface to the client side WebSockets

from org.transcrypt.stubs.browser import WebSocket,\
    __new__, __pragma__, JSON


class RawWebsocket:
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
        print("RAW open", url)
        self._isopen = False
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
        # self._ws.connect()
        # self._ws.send('Wakey-wakey')
        # while self._ws.readyState != 1:
        #    print("RAW open end", self._ws.readyState)

    def send_raw(self, data_to_server) -> None:
        # self._ws.send(data_to_server)
        if self._isopen:
            self._ws.send(data_to_server)
        else:
            print('NOT sending (isopen=False)....', data_to_server)

    def is_open(self):
        return self._isopen

    def send(self, data_to_server) -> None:
        self.send_raw(data_to_server)

    def close(self) -> None:
        self._ws.close()

    def on_open_cb(self, event) -> None:
        print('on_open_cb')

    def on_error_cb(self, event) -> None:
        print('on_error_cb')

    def on_message_cb(self, event) -> None:
        print('on_message_cb')


class JSONWebsocket(RawWebsocket):
    """A websocket that converts all data to JSON before sending it to the server.
    It also expects the data from the server to be in JSON format, and converts this
    data before passing it to the client via the on_message_JSON method.
    """
    def __init__(self, url: str, protocol_lst: list) -> None:
        super().__init__(url, protocol_lst)

    def send(self, data_to_server) -> None:
        """Convert the data structure to JSON before sending it
        to the server."""
        print("send {}".format(data_to_server))
        self.send_raw(JSON.stringify(data_to_server))

    def on_message_JSON(self, data) -> None:
        """This method will be called whenever a message is received from the server.
        The data from the server will be provided in a javascript data structure.
        """
        pass

    def on_message_cb(self, event) -> None:
        datain = JSON.parse(event.data)
        self.on_message_JSON(datain)
