""" This is the 'main program' of the client side program that runs in the browser.
    It opens a websocket to the stocky server and passes control to a wccontroller instance.
"""
import qailib.transcryptlib.genutils as genutils
import qailib.transcryptlib.websocket as websocket
import qailib.transcryptlib.serversocket as serversock
import webclient.wccontroller as wccontroller
if genutils.for_transcrypt:
    from org.transcrypt.stubs.browser import location


if genutils.for_transcrypt:
    log = genutils.log

    # this is the main program that runs in the browser when the page is loaded
    print('hello world')
    # all we do is open a websocket and start the main program
    # urlstr = 'wss://localhost:6000/goo'
    urlstr = 'wss://{}/goo'.format(location.host)
    print("URLSTR is '{}'".format(urlstr))
    rawsock = websocket.RawWebsocket(urlstr, ['/'])
    mysock = serversock.JSONserver_socket('scosock', rawsock)
    print("entering stocky mainprog")
    main_app = wccontroller.stocky_mainprog('webclient', mysock)
