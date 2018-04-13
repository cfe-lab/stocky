
import pytest

import logging

from gevent.queue import Queue

import serverlib.commlink as commlink
import serverlib.TLSAscii as TLSAscii


class Test_TLSAscii:

    def setup_method(self) -> None:
        self.msgQ = Queue()
        logger = logging.Logger("testing")
        self.cl = commlink.DummyCommLink({'logger': logger})
        if not self.cl.is_alive():
            print("Test cannot be performed: commlink is not alive")
        idstr = self.cl.id_string()
        print("commlink is alive. Ident is {}".format(idstr))
        self.tls = TLSAscii.TLSReader(self.msgQ, logger, self.cl)

    def test_radar01(self):
        EPCcode = "123456"
        self.tls.RadarSetup(EPCcode)
        self.tls.RadarGet()
        # assert isinstance(rssi, int), "int expected"
        # print("GOOT {}".format(rssi))
        # assert False, "force fail"

    def test_RFIDparams01(self):
        assert len(TLSAscii.rfid_lst) == len(TLSAscii.rfid_order_lst)

    def test_RFIDparams02(self):
        exp_str = '-al on'
        rr = TLSAscii.RFIDParams(do_alert='on')
        retstr = rr.tostr()
        if retstr != exp_str:
            print("unexpected '{}', expected '{}'".format(retstr, exp_str))
            raise RuntimeError("RFIDParams fail")
        # assert False, "force fail"

    def test_RFIDparams03(self):
        exp_str = '-x '
        rr = TLSAscii.RFIDParams(reset_to_default=None)
        retstr = rr.tostr()
        if retstr != exp_str:
            print("unexpected '{}', expected '{}'".format(retstr, exp_str))
            raise RuntimeError("RFIDParams fail")
