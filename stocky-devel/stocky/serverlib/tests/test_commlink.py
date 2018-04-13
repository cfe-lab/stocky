import pytest

import logging

import serverlib.commlink as commlink


CommLinkClass = commlink.DummyCommLink


class Test_Commlink:

    def setup_method(self) -> None:
        logger = logging.Logger("testing")
        self.cl = CommLinkClass({'logger': logger})
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

    def test_clresponse01(self):
        """Test CLResponse class"""
        csval = "iv. "
        test_lst = [("CS", csval),
                    ("ME", "hello")]
        clresp = commlink.CLResponse(test_lst)
        assert clresp is not None, "Failed to instantiate CLResponse"
        cslst = clresp["CS"]
        assert isinstance(cslst, list), "List expected"
        assert len(cslst) == 1, "expected length 1"
        csgot = cslst[0]
        assert isinstance(csgot, str), "Str expected"
        assert csgot == csval, "CS mismatch"

    def test_cl_return_message01(self) -> None:
        testy_lst = [([("ME", "hello")], "hello"),
                     ([("AA", "funny")], None)]
        for test_lst, resp_exp in testy_lst:
            clresp = commlink.CLResponse(test_lst)
            resp_got = clresp._return_message()
            assert resp_got == resp_exp, "unexpected RespTuple"

    def test_cl_return_code01(self):
        testy_lst = [([("ME", "hello"), ('OK', "")], commlink.BaseCommLink.RC_OK),
                     ([("ME", "hello"), ('ER', "099")], 99)]
        for test_lst, resp_exp in testy_lst:
            clresp = commlink.CLResponse(test_lst)
            resp_got = clresp.return_code()
            assert resp_got == resp_exp, "unexpected respcode"

    def test_dummyCL_valid01(self):
        """Issue a valid command and check its result."""
        clresp = self.cl._blocking_cmd(".ec -p")
        assert isinstance(clresp, commlink.CLResponse), "CLResponse expected"
        ret_code = clresp.return_code()
        if ret_code != commlink.BaseCommLink.RC_OK:
            raise RuntimeError("unexpected RESP {}".format(ret_code))
        # assert False, "force fail"

    def test_dummyCL_valid_with_comment01(self):
        """Issue a valid command with a comment and check its result."""
        comment_str = "hello there"
        clresp = self.cl._blocking_cmd(".ec -p", comment_str)
        assert isinstance(clresp, commlink.CLResponse), "CLResponse expected"
        ret_code = clresp.return_code()
        if ret_code != commlink.BaseCommLink.RC_OK:
            raise RuntimeError("unexpected RESP {}".format(ret_code))
        cdict = clresp.get_comment_dct()
        assert isinstance(cdict, dict), "Dict expected"
        got_commentstr = cdict.get('CMT', None)
        if got_commentstr != comment_str:
            print("CDICT {}".format(cdict))
            raise RuntimeError("unexpected comment")

    def test_dummyCL_invalid01(self):
        """Issuing an invalid command should raise a RuntimeError"""
        with pytest.raises(RuntimeError):
            self.cl._blocking_cmd(".bla -p")
        # assert False, "force fail"
