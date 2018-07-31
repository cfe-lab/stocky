# This is the 'main program' of the client side program that runs in the browser.
# It is a websocket program


import qailib.transcryptlib.genutils as genutils
import qailib.transcryptlib.serversocket as serversock
import wccontroller

log = genutils.log

# this is the main program that runs when the page is loaded
log('hello world')
# all we do is open a websocket and start the main program
mysock = serversock.server_socket('scosock', 'ws://localhost:5000/goo', ['/'])
if not mysock.is_open():
    print("FAILED TO PUT ON MY SOCKS!")
main_app = wccontroller.stocky_mainprog('webclient', mysock)
