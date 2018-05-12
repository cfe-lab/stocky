# import pytest

import math
import logging

from gevent.queue import Queue

import serverlib.commlink as commlink
import serverlib.TLSAscii as TLSAscii
from webclient.commonmsg import CommonMSG


class Test_TLSAscii:

    def setup_method(self) -> None:
        self.msgQ = Queue()
        logger = logging.Logger("testing")
        self.cl = commlink.DummyCommLink({'logger': logger})
        if not self.cl.is_alive():
            print("Test cannot be performed: commlink is not alive")
        idstr = self.cl.id_string()
        print("commlink is alive. Ident is {}".format(idstr))
        self.radar_ave_num = 1
        self.tls = TLSAscii.TLSReader(self.msgQ, logger, self.cl, self.radar_ave_num)

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

    def test_RI2dist01(self):
        rivals = [(-65, 1.0),
                  (-70, 1.53),
                  (-62, 0.77)]
        EPS = 0.01
        for ri, exp_val in rivals:
            got_val = TLSAscii.RunningAve.RI2dist(ri)
            # print(" {} {}  {}".format(ri, exp_val, got_val))
            if math.fabs(got_val - exp_val) > EPS:
                raise RuntimeError("unexpected distance RI: {}, exp: {}, got:  {}".format(ri,
                                                                                          exp_val,
                                                                                          got_val))
        # assert False, "force fail"

    def test_convert_msg(self):
        rone = [('CS', '.iv'),
                ('EP', '000000000000000000001242'), ('RI', '-64'),
                ('EP', '000000000000000000001243'), ('RI', '-55'),
                ('EP', '000000000000000000001241'),
                ('RI', '-62'), ('EP', '000000000000000000001236'),
                ('RI', '-59'), ('EP', '000000000000000000001234'),
                ('RI', '-59'), ('EP', '000000000000000000001237'),
                ('RI', '-62'), ('EP', '000000000000000000001240'),
                ('RI', '-65'), ('EP', '000000000000000000001235'),
                ('RI', '-66'), ('EP', '000000000000000000001239'),
                ('RI', '-59'), ('OK', '')]
        rtwo = [('CS', '.bc'), ('ME', 'No barcode found'), ('ER', '006')]
        rthree = [('CS', '.iv'), ('ME', 'No Transponder found'), ('ER', '005')]
        # rfour: remove RI entries from rone.
        rfour = [t for t in rone if t[0] != 'RI']
        rfive = [('CS', '.iv A{"MSG":"31","CMT":"RAD"}B'),
                 ('EP', '000000000000000000001237'), ('RI', '-63'),
                 ('EP', '000000000000000000001235'), ('RI', '-60'),
                 ('EP', '000000000000000000001238'), ('RI', '-68'),
                 ('EP', '000000000000000000001239'), ('RI', '-70'),
                 ('EP', '000000000000000000001243'), ('RI', '-52'),
                 ('EP', '000000000000000000001236'), ('RI', '-60'),
                 ('EP', '000000000000000000001242'), ('RI', '-67'),
                 ('EP', '000000000000000000001234'), ('RI', '-66'), ('OK', '')]
        rsix = [t for t in rfive if t[0] != 'RI']
        radar_mode = TLSAscii.tls_mode(TLSAscii.tls_mode.radar)
        stock_mode = TLSAscii.tls_mode(TLSAscii.tls_mode.stock)
        undef_mode = TLSAscii.tls_mode(TLSAscii.tls_mode.undef)

        rad_dat = CommonMSG.MSG_RF_RADAR_DATA
        stk_dat = CommonMSG.MSG_RF_STOCK_DATA
        cmd_dat = CommonMSG.MSG_RF_CMD_RESP
        testvals = [(rone, radar_mode, rad_dat, 9),
                    (rone, stock_mode, stk_dat, 9),
                    (rone, undef_mode, cmd_dat, len(rone)),
                    (rtwo, radar_mode, rad_dat, 0),
                    (rtwo, stock_mode, stk_dat, 0),
                    (rtwo, undef_mode, cmd_dat, len(rtwo)),
                    (rthree, radar_mode, rad_dat, 0),
                    (rthree, stock_mode, stk_dat, 0),
                    (rthree, undef_mode, cmd_dat, len(rthree)),
                    (rfour, radar_mode, rad_dat, None),
                    (rfour, stock_mode, stk_dat, 9),
                    (rfour, undef_mode, cmd_dat, len(rfour)),
                    (rfive, radar_mode, rad_dat, 8),
                    (rfive, stock_mode, rad_dat, 8),
                    (rfive, undef_mode, rad_dat, 8),
                    (rsix, radar_mode, rad_dat, None),
                    (rsix, stock_mode, stk_dat, None),
                    (rsix, undef_mode, cmd_dat, None)]
        for testlst, test_mode, expected_msg, exp_val in testvals:
            print("\n\n-------------------------")
            testin = commlink.CLResponse(testlst)
            self.tls.mode = test_mode
            # we must reset the running average in order to avoid side effects...
            self.tls.runningave.reset_average()
            got_val = self.tls._convert_message(testin)
            if got_val is not None:
                assert isinstance(got_val, CommonMSG), "expected a CommonMSG instance"
            if exp_val is None:
                if got_val is not None:
                    print("got_val: inp: {}, mode: {}, exp_msg: {}, exp_val: {}".format(testlst,
                                                                               test_mode,
                                                                               expected_msg,
                                                                               exp_val))
                    raise RuntimeError("expected None: testin {}, expected: {}, got: {}".format(testin,
                                                                                                exp_val,
                                                                                                got_val))
            else:
                # we do a relaxed test of correctnes
                if got_val is None:
                    print("inp: {}, mode: {}, exp_msg: {}, exp_val: {}".format(testlst,
                                                                               test_mode,
                                                                               expected_msg,
                                                                               exp_val))
                    raise RuntimeError('got None, expected {}'.format(exp_val))
                else:
                    dct = got_val.as_dict()
                    assert dct['msg'] == expected_msg, "unexpected msg type"
                    dat = dct['data']
                    if not isinstance(dat, list) or len(dat) != exp_val:
                        print("expected data as a list of length exp_val = {}".format(exp_val))
                        print("inp: {}, mode: {}, exp_msg: {}, exp_val: {}".format(testlst,
                                                                                   test_mode,
                                                                                   expected_msg,
                                                                                   exp_val))
                        raise RuntimeError("unexpected output")
