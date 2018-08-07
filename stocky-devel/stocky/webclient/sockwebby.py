
# This program is to be launched as a Web Service from within the browser
import typing
from org.transcrypt.stubs.browser import addEventListener, postMessage, __pragma__
import qailib.transcryptlib.websocket as websocket


def postMSG(cmd: str, arg: typing.Any) -> None:
    dd = {'cmd': cmd, 'arg': arg}
    postMessage(dd)


class MessageWebsocket(websocket.RawWebsocket):
    """A raw socket that talks directly to the stocky server and relays
    incoming messages to the other javascript task"""
    def on_open_cb(self, event) -> None:
        print('MSG: on_open_cb')
        postMSG('open', None)

    def on_error_cb(self, event) -> None:
        print('MSG: on_error_cb')
        postMSG('error', None)

    def on_message_cb(self, event) -> None:
        print('MSG: on_message_cb')
        postMSG('newmessage', event.data)


proto_lst = ['/']
mysock = MessageWebsocket('ws://localhost:5000/goo', proto_lst)


def mainloop(event) -> None:
    """This is the main event loop which is used to talk to the other
    javascript process.
    """
    msgdct = event.data
    cmd = msgdct.get('cmd', None)
    arg = msgdct.get('arg', None)
    if cmd is None:
        print("received a None command")
        return
    if cmd == 'send':
        mysock.send(arg)
    elif cmd == 'close':
        mysock.close()
    else:
        print("unknown command {}".format(cmd))


print("Hello from sockwebby!")
addEventListener('message', mainloop, False)
