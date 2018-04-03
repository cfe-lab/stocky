#!/usr/bin/env python3

# a small interface to inotify
import argparse
import sys

import usb

import inotify.adapters
import inotify.constants as iconst

import threading
# import gevent
# from multiprocessing import Process, Lock


USB_DIR = "/dev/bus/usb"

MY_EVENT_MASK = iconst.IN_CREATE + iconst.IN_DELETE
# MY_EVENT_MASK = iconst.IN_ALL_EVENTS


def get_USB_set():
    """Return a set of integer tuples (idvendor, idproduct) describing the currently
    connected USB devices."""
    return set([(dev.idVendor, dev.idProduct) for dev in usb.core.find(find_all=True)])

# class CheckerThread(gevent.Greenlet):
# class CheckerThread(Process):
class CheckerThread(threading.Thread):

    def __init__(self):
        super().__init__()
        self._acc_lock = threading.Lock()
        # self._acc_lock = gevent.lock.Semaphore()
        # self._acc_lock = Lock()
        self.watchtab = {}
        self.curset = set()
        self._set_set()
        # self.setDaemon(True)

    def _set_set(self) -> None:
        with self._acc_lock:
            self.prevset = self.curset
            self.curset = get_USB_set()
            # check for new devices
            wtab = self.watchtab
            for devtup, cbfunc in [(newdevtup, wtab[newdevtup]) for newdevtup in self.curset - self.prevset if newdevtup in wtab]:
                cbfunc(devtup, True)
            # check for removed devices
            for devtup, cbfunc in [(olddevtup, wtab[olddevtup]) for olddevtup in self.prevset - self.curset if olddevtup in wtab]:
                cbfunc(devtup, False)
            # print("len {}".format(len(self.usbset)))

    def get_set(self) -> set:
        with self._acc_lock:
            retval = self.curset
        return retval

    def check_loop(self) -> None:
        print("#enter check_loop!")
        lverb = False
        i = inotify.adapters.InotifyTree(USB_DIR, MY_EVENT_MASK)
        for event in i.event_gen(yield_nones=False):
            (_, ev_type_namelst, path, filename) = event
            if lverb:
                print("detected USB event! {}".format(event))
                print("PATH=[{}] FILENAME=[{}] EVENT_TYPES={}".format(
                    path, filename, ev_type_namelst))
            # print("ACTING on USB event! {}".format(event))
            self._set_set()
            # print("\n\n")

    def _registerCallBack(self, prodtup, cbfunc) -> bool:
        """Register a callback function that will be called whenever a particular
        device is plugged in/out.
        Return := 'the callback was registered successfully'

        The provided callback func must expect (prod_tuple, isPresent: bool),
        where prod_tuple is a 2-tuple of int (idvendor, idproduct)
        isPresent: 'the device is currently plugged in'
        """
        # check the arguments etx of the provided cbfunc
        self.watchtab[prodtup] = cbfunc
        return True

    def run(self):
        self.check_loop()

usb_checker = CheckerThread()


class USBState:
    def __init__(self, prod_tup) -> None:
        self.check_tup = prod_tup

    def isPresent(self) -> bool:
        """Return := 'the device is present (i.e. plugged in) '
        """
        return self.check_tup in usb_checker.get_set()

    def registerCallBack(self, cbfunc) -> bool:
        return usb_checker._registerCallBack(self.check_tup, cbfunc)


def printit(tupy, ispresent):
    print("{}:{}:{}".format(tupy[0], tupy[1], ispresent), flush=True)


def main():
    parser = argparse.ArgumentParser(description='Listen for USB events')
    parser.add_argument('-m', action="store", dest="m", type=int,
                        help='manufacturer ID', required=True)
    parser.add_argument('-p', action="store", dest="p", type=int,
                        help='Product ID', required=True)
    args = parser.parse_args()
    print("#GOOT {} {}".format(args.m, args.p))
    #
    # NOTE: we return the state whenever queried, but also write out
    # any state changes we detect by callback
    prod_tup = args.m, args.p
    usb_checker.start()
    usbstate = USBState(prod_tup)
    print("#Hello!")
    usbstate.registerCallBack(printit)
    printit(prod_tup, usbstate.isPresent())
    while True:
        # NOTE: we don't care what the string is, we just wait for a linefeed
        for string in sys.stdin:
            # print("yeehaa {}".format(string))
            printit(prod_tup, usbstate.isPresent())
    print("#Goodbye!")


if __name__ == "__main__":
    main()
