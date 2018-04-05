
import pytest

import serverlib.commlink as commlink
import serverlib.TLSAscii as TLSAscii


class Test_TLSAscii:

    def setup_method(self) -> None:
        self.cl = commlink.DummyCommLink("bla", {})
        if not self.cl.is_alive():
            print("Test cannot be performed: commlink is not alive")
        idstr = self.cl.id_string()
        print("commlink is alive. Ident is {}".format(idstr))

    def test_cl_response_codes_len(self) -> None:
        """All commlink response codes must be of length 2"""
        ll = commlink.resp_code_lst
        assert all([len(ret_code) == 2 for ret_code in ll])

    def test_cl_response_codes_unique(self) -> None:
        """All defined commlink response codes must be unique"""
        ll = commlink.resp_code_lst
        assert len(ll) == len(commlink.resp_code_set), "commlink response code not unique"

    def test_cl_command_codes_len(self) -> None:
        """All commlink command codes must be of length 2"""
        ll = commlink.command_lst
        assert all([len(ret_code) == 2 for ret_code in ll])

    def test_cl_command_codes_unique(self) -> None:
        """All defined commlink command codes must be unique"""
        ll = commlink.command_lst
        assert len(ll) == len(commlink.command_set), "commlink command code not unique"

    def test_cl_line2resp(self) -> None:
        """Test BaseCommLink.line_2_resptup with legal and illegal input"""
        test_lst = [("AB: hello", ("AB", "hello")),
                    ("BLA:goo", None),
                    ("AA:funny", None),
                    (" ", None)]
        for test_line, resp_exp in test_lst:
            resp_got = commlink.BaseCommLink._line_2_resptup(test_line)
            assert resp_got == resp_exp, "unexpected RespTuple"

    def test_dummyCL01(self):
        """Issue a valid raw command."""
        self.cl.raw_send_cmd(".ec -p")

    def test_dummyCL_valid01(self):
        """Issue a valid command and check its result."""
        resp = self.cl.execute_cmd(".ec -p")
        if resp != commlink.OK_RESP_LIST:
            raise RuntimeError("unexpected RESP {}".format(resp))
        # assert False, "force fail"

    def test_dummyCL_invalid01(self):
        """Issue an invalid command and check its result."""
        with pytest.raises(RuntimeError):
            self.cl.execute_cmd(".bla -p")
        # assert False, "force fail"

    def test_radar01(self):
        EPCcode = "123456"
        self.cl.RadarSetup(EPCcode)
        rssi = self.cl.RadarGet()
        assert isinstance(rssi, int), "int expected"
        print("GOOT {}".format(rssi))
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
