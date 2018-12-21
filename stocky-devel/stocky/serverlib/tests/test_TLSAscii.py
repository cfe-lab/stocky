
import typing
import math
import logging

import pytest
from gevent.queue import Queue

import serverlib.commlink as commlink
import serverlib.TLSAscii as TLSAscii
from webclient.commonmsg import CommonMSG
import serverlib.tests.test_commlink as test_commlink


class DeadCommLink(commlink.BaseCommLink):
    """A dummy commlink used for testing"""

    def __init__(self, cfgdct: dict) -> None:
        super().__init__(cfgdct)

    def open_device(self) -> typing.Any:
        return None

    def _is_alive(self, doquick: bool = True) -> bool:
        return False

    def id_string(self) -> str:
        return "DeadCommLink"


class Test_TLSAscii:

    def setup_method(self) -> None:
        self.msgQ = Queue()
        self.logger = logging.Logger("testing")
        self.cl = test_commlink.DummyCommLink({'logger': self.logger})
        self.deadcl = DeadCommLink({'logger': self.logger})
        if not self.cl._is_alive():
            print("Test cannot be performed: commlink is not alive")
        idstr = self.cl.id_string()
        print("commlink is alive. Ident is {}".format(idstr))
        self.radar_ave_num = 1
        self.tls = TLSAscii.TLSReader(self.msgQ,
                                      self.logger,
                                      self.cl,
                                      self.radar_ave_num)
        self.good_epc = '000000000000000000001237'
        self.bad_epc = "123456"

    def test_radar01(self):
        """BT_set_radar_mode() with valid/invalid arguments should behave
        appropriately."""
        with pytest.raises(ValueError):
            self.tls.BT_set_radar_mode(self.bad_epc)
        # --
        self.tls.BT_set_radar_mode(self.good_epc)
        self.tls.RadarGet()
        # assert isinstance(rssi, int), "int expected"
        # print("GOOT {}".format(rssi))
        # assert False, "force fail"

    def test_is_radarmode01(self):
        """is_in_radarmode() should return the expected value depending on actual mode."""
        res = self.tls.is_in_radarmode()
        assert isinstance(res, bool), "expected bool"
        assert not res, 'not radarmode expected!'
        self.tls.mode = TLSAscii.tls_mode.radar
        res = self.tls.is_in_radarmode()
        assert isinstance(res, bool), "expected bool"
        assert res, 'radarmode expected!'

    def test_barcodeparams_valid(self):
        """Creating and setting valid BarcodeParams should work."""
        bb = TLSAscii.BarcodeParams(True, True, 1)
        assert bb is not None, "alert failed"
        bcstr = bb.tostr()
        assert isinstance(bcstr, str), "expected a string"
        self.tls.set_readbarcode_params(bb)
        self.tls.readbarcode(bb)

    def test_barcodeparams_invalid(self):
        """Creating a BarcodeParams instance with invalid data should raise a ValueError."""
        with pytest.raises(ValueError):
            TLSAscii.BarcodeParams(True, True, 22)

    def test_alertparams01(self):
        """Creating a TLSAscii.AlertParams instance with valid arguments does work."""
        aa = TLSAscii.AlertParams(buzzeron=False, vibrateon=True,
                                  vblen=TLSAscii.BuzzViblen('med'),
                                  pitch=TLSAscii.Buzzertone('med'))
        assert aa is not None, "alert failed"
        self.tls.doalert(aa)
        self.tls.set_alert_default(aa)

    def test_abort_cmd(self):
        """Calling send_abort() to interrupt a command does work."""
        self.tls.send_abort()

    def test_RFIDparams_configOK(self):
        """The TLSAscii.rfid_lst and TLSAscii.rfid_order_lst lists have the same length"""
        assert len(TLSAscii.rfid_lst) == len(TLSAscii.rfid_order_lst)

    def test_RFIDparams_alert(self):
        """TLSAscii.RFIDParams(do_alert='on').tostr() returns the expected string"""
        exp_str = '-al on'
        rr = TLSAscii.RFIDParams(do_alert='on')
        retstr = rr.tostr()
        if retstr != exp_str:
            print("unexpected '{}', expected '{}'".format(retstr, exp_str))
            raise RuntimeError("RFIDParams fail")
        # assert False, "force fail"

    def test_RFIDparams_reset_to_defaults(self):
        """TLSAscii.RFIDParams(reset_to_default=None).tostr() returns the expected string"""
        exp_str = '-x '
        rr = TLSAscii.RFIDParams(reset_to_default=None)
        retstr = rr.tostr()
        if retstr != exp_str:
            print("unexpected '{}', expected '{}'".format(retstr, exp_str))
            raise RuntimeError("RFIDParams fail")

    def test_set_date_time(self):
        """Test legal and illegal arguments to set_date_time(), which should raise
        exceptions when appropriate.
        """
        # try with wrong values
        for dt in [(2009, 10, 20, 25, 60, 60),
                   (2009, 10, 20, 23, 60, 59),
                   (2009, 10, 20, 23, 59, 60),
                   (2009, 10, 20, 25, 59, 59),
                   (2009, 10, 36, 23, 59, 59),
                   (2009, 13, 20, 23, 59, 59),
                   (1999, 13, 20, 23, 59, 59)]:
            with pytest.raises(ValueError):
                print('testing {}'.format(dt))
                self.tls.set_date_time(*dt)
        # should work
        ok_tup = (2009, 10, 20, 22, 59, 59)
        self.tls.set_date_time(*ok_tup)
        # replace each argument with an int in turn: should fail...
        for i in range(len(ok_tup)):
            broken_lst = list(ok_tup)
            broken_lst[i] = 'bla'
            dt = tuple(broken_lst)
            with pytest.raises(TypeError):
                self.tls.set_date_time(*dt)
        # this should work
        dt = (2009, 10, 20, 22, 59, 59)
        self.tls.set_date_time(*dt)

    def test_RFIDparams04(self):
        """TLSAscii.RFIDParams(wonky_arg=99) should raise a RuntimeError."""
        with pytest.raises(RuntimeError):
            TLSAscii.RFIDParams(wonky_arg=99)

    def test_runningave01(self):
        """A RunningAve instance with zero window averaging should raise a RuntimeError."""
        with pytest.raises(RuntimeError):
            TLSAscii.RunningAve(self.logger, 0)

    def test_stock_check_mode(self):
        """BT_set_stock_check_mode() should not crash"""
        self.tls.BT_set_stock_check_mode()

    def test_set_region(self):
        """Setting an invalid region code string should raise an exception.
           Setting a valid region code should not.
        """
        for reg, exc in [('BLA', ValueError),
                         (100, TypeError)]:
            with pytest.raises(exc):
                self.tls.set_region(reg)
        # NOTE: this should work, but we don't yet test for the generated output..
        self.tls.set_region('us')

    def test_runningave02(self):
        """Feeding RFID scan data into a TLSAscii.RunningAve instance should
        produce the expected average value."""
        ave_len = 2
        rone = [('CS', '.iv'),
                ('EP', '000000000000000000001242'), ('RI', '-65'), ('OK', '')]
        testin = commlink.CLResponse(rone)
        ra = TLSAscii.RunningAve(self.logger, ave_len)
        for i in range(2 * ave_len):
            ra.add_clresp(testin)
            assert len(ra._dlst) <= ave_len, "unexpected ave list"
            run_ave = ra.get_runningave()
            if i < ave_len-1:
                assert run_ave is None, "running ave not None for i = {} < ave_len={}".format(i, ave_len)
            else:
                assert run_ave is not None, "running ave is None for i> ave_len"

    def test_RI2dist01(self):
        """ TLSAscii.RunningAve.RI2dist should convert RI values into expected distance
          values."""
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

    def test_radardata01(self):
        """Invalid radar data (RI field) should result in RunningAve._radar_data()
           returning None."""
        rone = [('CS', '.iv'),
                ('EP', '000000000000000000001242'), ('RI', 'BLA'), ('OK', '')]
        for testlst in [rone]:
            testin = commlink.CLResponse(testlst)
            gotval = TLSAscii.RunningAve._radar_data(self.logger, testin)
            assert gotval is None, "expected None"

    def test_convert_msg(self):
        "Test  _convert_message() with a number of legal and illegal RFID messages"
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
        len_rone = len(rone)
        rtwo = [('CS', '.bc'), ('ME', 'No barcode found'), ('ER', '006')]
        len_rtwo = len(rtwo)
        rthree = [('CS', '.iv'), ('ME', 'No Transponder found'), ('ER', '005')]
        len_rthree = len(rthree)
        # rfour: remove RI entries from rone.
        rfour = [t for t in rone if t[0] != 'RI']
        len_rfour = len(rfour)
        rfive = [('CS', '.iv A{"MSG":"31","CMT":"RAD"}B'),
                 ('EP', '000000000000000000001237'), ('RI', '-63'),
                 ('EP', '000000000000000000001235'), ('RI', '-60'),
                 ('EP', '000000000000000000001238'), ('RI', '-68'),
                 ('EP', '000000000000000000001239'), ('RI', '-70'),
                 ('EP', '000000000000000000001243'), ('RI', '-52'),
                 ('EP', '000000000000000000001236'), ('RI', '-60'),
                 ('EP', '000000000000000000001242'), ('RI', '-67'),
                 ('EP', '000000000000000000001234'), ('RI', '-66'), ('OK', '')]
        # len_rfive = len(rfive)
        rsix = [t for t in rfive if t[0] != 'RI']
        radar_mode = TLSAscii.tls_mode(TLSAscii.tls_mode.radar)
        stock_mode = TLSAscii.tls_mode(TLSAscii.tls_mode.stock)
        # undef_mode = TLSAscii.tls_mode(TLSAscii.tls_mode.undef)

        rad_dat = CommonMSG.MSG_RF_RADAR_DATA
        # stk_dat = CommonMSG.MSG_RF_STOCK_DATA
        stk_dat = CommonMSG.MSG_RF_CMD_RESP
        # cmd_dat = CommonMSG.MSG_RF_CMD_RESP
        testvals = [(rone, radar_mode, rad_dat, 9),
                    (rone, stock_mode, stk_dat, len_rone),
                    # (rone, undef_mode, cmd_dat, len(rone)),
                    (rtwo, radar_mode, rad_dat, 0),
                    (rtwo, stock_mode, stk_dat, len_rtwo),
                    # (rtwo, undef_mode, cmd_dat, len(rtwo)),
                    (rthree, radar_mode, rad_dat, 0),
                    (rthree, stock_mode, stk_dat, len_rthree),
                    # (rthree, undef_mode, cmd_dat, len(rthree)),
                    (rfour, radar_mode, rad_dat, None),
                    (rfour, stock_mode, stk_dat, len_rfour),
                    # (rfour, undef_mode, cmd_dat, len(rfour)),
                    (rfive, radar_mode, rad_dat, 8),
                    (rfive, stock_mode, rad_dat, 8),
                    # (rfive, undef_mode, rad_dat, 8),
                    (rsix, radar_mode, rad_dat, None),
                    (rsix, stock_mode, stk_dat, None)]
        # (rsix, undef_mode, cmd_dat, None)]
        #
        # pass in messages with a radarsetup comment
        # one OK, one error message
        # ivcmd = '.iv A{"MSG":"31","CMT":"radarsetup"}B'
        # rad1 = [('CS', ivcmd), ('ME', 'No Transponder found'), ('ER', '005')]
        # rad2 = [('CS', ivcmd),
        #        ('EP', '000000000000000000001242'), ('RI', '-67'),
        #        ('EP', '000000000000000000001234'), ('RI', '-66'), ('OK', '')]
        # testvals.append((rad1, undef_mode, cmd_dat, 3))
        # testvals.append((rad2, undef_mode, rad_dat, None))

        #
        # pass in messages with an IVreset comment
        # ivcmd = '.iv A{"MSG":"31","CMT":"IVreset"}B'
        # rad1 = [('CS', ivcmd), ('ME', 'No Transponder found'), ('ER', '005')]
        # rad2 = [('CS', ivcmd),
        #        ('EP', '000000000000000000001242'), ('RI', '-67'),
        #        ('EP', '000000000000000000001234'), ('RI', '-66'), ('OK', '')]
        # testvals.append((rad1, undef_mode, cmd_dat, 3))
        # testvals.append((rad2, undef_mode, rad_dat, None))

        # pass in messages with an unknown commentstring
        # should return None in both cases
        # ivcmd = '.iv A{"MSG":"31","CMT":"WONKYCOMMENT"}B'
        # rad1 = [('CS', ivcmd), ('ME', 'No Transponder found'), ('ER', '005')]
        # rad2 = [('CS', ivcmd),
        #        ('EP', '000000000000000000001242'), ('RI', '-67'),
        #        ('EP', '000000000000000000001234'), ('RI', '-66'), ('OK', '')]
        # testvals.append((rad1, undef_mode, cmd_dat, None))
        # testvals.append((rad2, undef_mode, rad_dat, None))

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
                        print("data is '{}'".format(dat))
                        fmtstr = "inp: {},\n mode: {},\n exp_msg: {},\n exp_val(length): {}, actual length: {}"
                        print(fmtstr.format(testlst,
                                            test_mode,
                                            expected_msg,
                                            exp_val, len(dat)))
                        raise RuntimeError("unexpected output")

        # an illegal TLS mode should raise an exception..
        # THis is no longer true... instead we expect None
        testin = commlink.CLResponse(rone)
        self.tls.mode = 'bla'
        # with pytest.raises(RuntimeError):
        resp = self.tls._convert_message(testin)
        if resp is not None:
            raise RuntimeError("expected None")

    def test_sendRFIDmsg(self):
        """Test behaviour of send_RFID_msg() with a number of valid/ invalid
        arguments. E.g. sending an instance other than a CommonMSG should
        raise an exception.
        """
        with pytest.raises(TypeError):
            self.tls.send_RFID_msg('bla')

        cm = CommonMSG(CommonMSG.MSG_WC_RADAR_MODE, False)
        self.tls.send_RFID_msg(cm)
        assert self.tls.mode == TLSAscii.tls_mode.stock

        cm = CommonMSG(CommonMSG.MSG_WC_RADAR_MODE, True)
        self.tls.send_RFID_msg(cm)
        assert self.tls.mode == TLSAscii.tls_mode.radar

        cm = CommonMSG(CommonMSG.MSG_SV_GENERIC_COMMAND, '.iv')
        self.tls.send_RFID_msg(cm)
        assert self.tls.mode == TLSAscii.tls_mode.stock

        cm = CommonMSG(CommonMSG.MSG_SV_RAND_NUM, 'bla')
        with pytest.raises(RuntimeError):
            self.tls.send_RFID_msg(cm)
        # assert self.tls.mode == TLSAscii.tls_mode.undef
        # assert self.tls.mode == TLSAscii.tls_mode.stock

    def test_is_valid_EPC(self):
        """TLSAscii.is_valid_EPC(epc) should return the expected value
        on valid/invalid input"""
        for epc, exp_val in [('bla', False),
                             ('000000000000000000001237', True),
                             ('0000000AB000000000001237', True),
                             ('0000000GF000000000001237', False),
                             (100, False)]:
            res = TLSAscii.is_valid_EPC(epc)
            assert isinstance(res, bool), 'expected a bool'
            if res != exp_val:
                raise RuntimeError("unexpected res={} for '{}'".format(res, epc))

    def test_set_bluetooth01(self):
        """set_bluetooth() should raise a TypeError on bad input, and
        not do so on good input."""
        for bad_dat in [(1, 'bla', 'blu', 'bt_name', True, 'pcod'),
                        (True, 100, 'blu', 'bt_name', True, 'pcod'),
                        (True, 'bla', 'blu', 'bt_name', 1, 'pcod')]:
            with pytest.raises(TypeError):
                self.tls.set_bluetooth(*bad_dat)
        # the wrong pcode...
        bad_dat = (True, 'bla', 'blu', 'bt_name', True, 'pcode')
        with pytest.raises(ValueError):
            self.tls.set_bluetooth(*bad_dat)
        # should work
        good_dat = (True, 'bla', 'blu', 'bt_name', True, '1234')
        self.tls.set_bluetooth(*good_dat)

    def test_write_userbank01(self):
        """write_user_bank() should raise an appropriate exception
        on bad input and not do so on good input."""
        valid_data = '0123ABCDEF89'
        with pytest.raises(ValueError):
            self.tls.write_user_bank(self.bad_epc, valid_data)
        # --
        for dat, exc in [(100, TypeError),
                         ('fgrt', ValueError),
                         ('AB10F', ValueError)]:
            with pytest.raises(exc):
                self.tls.write_user_bank(self.good_epc, dat)
        self.tls.write_user_bank(self.good_epc, valid_data)

    def test_read_userbank01(self):
        """read_user_bank() should raise ValueError on bad input and
        not do so on good input.
        """
        with pytest.raises(ValueError):
            self.tls.read_user_bank(self.bad_epc, 4)
        # --
        for numch, exc in [('bla', TypeError),
                           (11, ValueError)]:
            with pytest.raises(exc):
                self.tls.read_user_bank(self.good_epc, numch)
        self.tls.read_user_bank(self.good_epc, 8)
