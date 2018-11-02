"""Provide an abstract base class for a websocket connection on the webclient side
   that is also a base_obj.
   This module is designed to be compiled by both Cpython and Transcrypt.
"""

import typing
import qailib.common.base as base


class base_server_socket(base.base_obj):
    def __init__(self, idstr):
        super().__init__(idstr)

    def send(self, data_to_server: typing.Any) -> None:
        """Send data to the server over the websocket.

        Args:
           data_to_server: the data to send over the socket.
              The data must be prepared for transmission (e.g. converted to JSON)
              before calling this routine.
        Note:
           This routine must be overridden in subclasses.
        """
        print("base_server_socket: NOT sending {}".format(data_to_server))

    def on_message_JSON(self, data_from_server) -> None:
        """A Message call-back method.

        This is called with a javascript data structure whenever the client
        receives a message from the server.

        Args:
           data_from_server: the data received from the server.

        Note:
           In this routine, we pass the received message to any observers listening
           via the base_obj signalling mechanism.
        """
        # NOTE: we must convert the javascript data into a python dict
        msg_dct = dict(data_from_server)
        self.sndMsg(base.MSGD_SERVER_MSG, msg_dct)
