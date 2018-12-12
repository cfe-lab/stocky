""" A client-side websocket library
"""
import typing
from qailib.transcryptlib.genutils import for_transcrypt

if for_transcrypt:
    from org.transcrypt.stubs.browser import Array, typeof

from qailib.transcryptlib.websocket import BaseRawWebSocket, JSONWebsocket
from qailib.common.serversocketbase import base_server_socket
import qailib.common.base as base


def is_js_dict(v) -> bool:
    """
    Return := v is a javascript 'dict', i.e. an object, but not an array.
    (in javascript, both arrays and objects are objects)

    Returns:
       True iff v is a javascript object, i.e. dict, but not a javascript array.
    """
    return typeof(v) == 'object' and not Array.isArray(v)


def is_js_array(v) -> bool:
    """Return := v is a javascript array

    Returns:
       v is a javascrypt array.
    """
    return Array.isArray(v)


class clientsocket(base_server_socket):
    """A virtual base class for websockets on the client side of things..."""

    def on_open_cb(self, event) -> None:
        """This routine is called whenever the socket is open for communication.
           Simply send a base_obj message to signal that the websocket has come
           online.
        """
        self.sndMsg(base.MSGD_COMMS_ARE_UP, {})

    def on_close_cb(self, event) -> None:
        """This routine is called whenever the socket is closed for communication.

        This can happen, e.g., when the server has crashed.
           Simply send a base_obj message to signal that the websocket has
           gone offline.
        """
        self.sndMsg(base.MSGD_COMMS_ARE_DOWN, {})

    def on_message_JSON(self, data_from_server: typing.Any) -> None:
        """This is called with a javascript data structure whenever the client
        receives a message from the server.
        Here, convert the data into a python one and then pass the message to any
        observers listening.

        Args:
           data_from_server: a javascript dict data structure.
        """
        # NOTE: we must convert the javascript data into a python dict
        msg_dct = self.pythonify_dct(data_from_server)
        # print("server says: '{}' AND '{}'".format(data_from_server, msg_dct))
        print("on_messag_JSON: incoming message..")
        self.sndMsg(base.MSGD_SERVER_MSG, msg_dct)

    def pythonify_dct(self, in_js) -> typing.Any:
        """Convert a hierarchical javascript structure (typically a dict converted from JSON)
        into a python dict structure.

        Args:
           in_js: The javascript data structure.
        Returns:
           A dict, a list or the original object if its neither.
        """
        if is_js_dict(in_js):
            retval = dict(in_js)
            for k, v in retval.items():
                if is_js_dict(v) or is_js_array(v):
                    retval[k] = self.pythonify_dct(v)
            return retval
        elif is_js_array(in_js):
            rv: typing.List[typing.Any] = []
            for i in in_js:
                if is_js_dict(i) or is_js_array(i):
                    rv.append(self.pythonify_dct(i))
                else:
                    rv.append(i)
            return rv
        else:
            return in_js


class JSONserver_socket(clientsocket, JSONWebsocket):
    """A websocket class that generates GUI events whenever a message
    is received from the server.
    Communication with the server occurs in JSON form.
    """
    def __init__(self, idstr: str, rawws: BaseRawWebSocket) -> None:
        clientsocket.__init__(self, idstr)
        JSONWebsocket.__init__(self, rawws)
        print("server_socket", self.is_open())
        # self._trackingdct: typing.Dict[int, html.base_obj] = {}

    def send(self, data_to_server) -> None:
        JSONWebsocket.send(self, data_to_server)
