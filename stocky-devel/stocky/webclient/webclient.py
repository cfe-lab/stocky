""" This is the 'main program' of the client side program that runs in the browser.
    It is a websocket program
"""

import qailib.transcryptlib.genutils as genutils
import qailib.transcryptlib.websocket as websocket
import qailib.transcryptlib.serversocket as serversock
# import qailib.transcryptlib.WebWorker as WebWorker
import wccontroller

log = genutils.log

# sockyWWname = 'webclient/__target__/sockwebby.js'

# this is the main program that runs in the browser when the page is loaded
print('hello world')
# ww = WebWorker.WebWorker('webclient/__javascript__/sockwebby.js')

# all we do is open a websocket and start the main program
rawsock = websocket.RawWebsocket('ws://localhost:5000/goo', ['/'])
# rawsock = WebWorker.SockyWebWorker(sockyWWname)
mysock = serversock.JSONserver_socket('scosock', rawsock)
if not mysock.is_open():
    print("FAILED TO PUT ON MY SOCKS!")
main_app = wccontroller.stocky_mainprog('webclient', mysock)
