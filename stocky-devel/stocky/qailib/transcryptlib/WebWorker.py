
# a thin interface over the Web Worker threading library, see
# https://www.w3schools.com/html/html5_webworkers.asp

# import typing
from org.transcrypt.stubs.browser import Worker,\
    __new__, __pragma__

# , addEventListener

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
        msgdct = event.data
        self.rcvWorkerMSG(msgdct)

    def sndWorkerMSG(self, msg: WWMSGDict) -> None:
        """Send the message dict to the WebWorker"""
        self._w.postMessage(msg)

    def rcvWorkerMSG(self, msg: WWMSGDict) -> None:
        """This method is called whenever the webworker sends
        a message to the main (spawning) task."""
        pass


class SockyWebWorker(WebWorker):
    """A web worker that gets messages from an external script, sockwebby.js, that sends
    us websocket events.
    This class pretends to be a websocket instance to the clients
    """
    def rcvWorkerMSG(self, msg: WWMSGDict) -> None:
        """This method is called whenever the webworker sends
        a message to the main (spawning) task.
        This receives any message ( a dict with cmd and arg entries)
        from the sockwebby.py program.
        Pass these on as if we were a websocket.
        """
        cmd = msg.get('cms', None)
        arg = msg.get('arg', None)
        if cmd is None:
            print("Socky webworker: none command")
            return
        if cmd == 'newmessage':
            pass

