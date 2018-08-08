
# a thin interface over the Web Worker threading library, see
# https://www.w3schools.com/html/html5_webworkers.asp

import typing
from org.transcrypt.stubs.browser import Worker,\
    __new__, __pragma__

import qailib.transcryptlib.websocket as websocket


# WWMSGDict = typing.Dict[str, typing.Any]
WWMSGDict = dict


class WebWorker:
    def __init__(self, filename: str) -> None:
        """Run the javascript code contained in the file 'filename'"""
        self._w = __new__(Worker(filename))
        __pragma__(
            'js', '{}',
            'self._w.onmessage = function(event){self._on_WWmessage_cb(event);}')
        print("hello from webworker {}".format(filename))

    def _on_WWmessage_cb(self, event) -> None:
        print('webworker on_message_cb')
        msgdct = dict(event.data)
        cmd = msgdct.get('cmd', None)
        arg = msgdct.get('arg', None)
        self.rcvWorkerMSG(cmd, arg)

    def sndWorkerMSG(self, cmd: str, arg: typing.Any) -> None:
        """Send the message dict to the WebWorker"""
        msgdct = {'cmd': cmd, 'arg': arg}
        self._w.postMessage(msgdct)

    def rcvWorkerMSG(self, cmd: str, arg: typing.Any) -> None:
        """This method is called whenever the webworker sends
        a message to the main (spawning) task."""
        pass


class SockyWebWorker(WebWorker, websocket.BaseRawWebSocket):
    """A web worker that gets messages from an external script, sockwebby.js, that sends
    us websocket events.
    This class pretends to be a websocket instance to the clients
    """
    def __init__(self, filename: str) -> None:
        WebWorker.__init__(self, filename)
        websocket.BaseRawWebSocket.__init__(self)

    def rcvWorkerMSG(self, cmd: str, arg: typing.Any) -> None:
        """This method is called whenever the webworker sends
        a message to the main (spawning) task.
        This receives any message ( a dict with cmd and arg entries)
        from the sockwebby.py program.
        Pass these on as if we were a websocket.
        """
        if cmd is None:
            print("Socky webworker: none command")
            return
        if cmd == 'newmessage':
            self.on_message_cb(arg)
        elif cmd == 'open':
            self.on_open_cb(arg)
        elif cmd == "error":
            self.on_error_cb(arg)
        else:
            print("SockyWebWorker: unknown cmd {}".format(cmd))

    def send_raw(self, data_to_server) -> None:
        self.sndWorkerMSG('send', data_to_server)

    def close(self) -> None:
        self._isopen = False
        self.sndWorkerMSG('close', None)
