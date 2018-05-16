import pytest

import logging

import serverlib.commlink as commlink


BaseCommLinkClass = commlink.BaseCommLink
DummyCommLinkClass = commlink.DummyCommLink

CommLinkClass = commlink.DummyCommLink


class Test_Commlink:

    def setup_method(self) -> None:
        self.logger = logging.Logger("testing")
        self.cl = CommLinkClass({'logger': self.logger})
        if not self.cl.is_alive():
            print("Test cannot be performed: commlink is not alive")
        idstr = self.cl.id_string()
        print("commlink is alive. Ident is {}".format(idstr))

    def test_baseCL_notimp(self):
        """The base should raise NotImplemented errors."""
        b = BaseCommLinkClass({'logger': self.logger})
        for func in [lambda b: b.raw_send_cmd('bla'),
                     lambda b: b.send_cmd('bla'),
                     lambda b: b.raw_read_response(),
                     lambda b: b.is_alive(),
                     lambda b: b.id_string()]:
            with pytest.raises(NotImplementedError):
                func(b)

    def test_baseCL_RC_string01(self):
        """Convert legal retcodes"""
        for retcode in commlink._tlsretcode_dct.keys():
            retstr = BaseCommLinkClass.RC_string(retcode)
            assert isinstance(retstr, str), "expected a string"

    def test_baseCL_RC_string02(self):
        """Convert illlegal retcodes"""
        for retcode in [-100, 50]:
            with pytest.raises(RuntimeError):
                BaseCommLinkClass.RC_string(retcode)

    def test_baseCL_comment_dct01(self):
        din = dict(a=1, b=5, c='99')
        code = BaseCommLinkClass.encode_comment_dict(din)
        assert isinstance(code, str), "string expected"
        dout = BaseCommLinkClass.extract_comment_dict(code)
        assert din == dout, "dicts are not the same!"

        # an invalid string must return a None dict
        for code in ["blaaa", "BA", "AkkkkkkkB"]:
            dout = BaseCommLinkClass.extract_comment_dict(code)
            assert dout is None, "expected None for dict"

    def test_dummy_get_cmd_from_str01(self):
        """Invalid commands should raise an exception"""
        for cmdstr in ['.iv bla',
                       'iv -x',
                       '.bb',
                       '.i AB  ']:
            with pytest.raises(RuntimeError):
                DummyCommLinkClass.get_cmd_from_str(cmdstr)

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

    def test_cl_return_code02(self):
        """A malformed error message should raise an exception."""
        testy_lst = [[("ME", "hello"), ('ER', "bla")],
                     [("ME", "hello"), ('ER', "")],
                     [("ME", "hello"), ('IV', "")],
                     ]
        for test_lst in testy_lst:
            clresp = commlink.CLResponse(test_lst)
            with pytest.raises(RuntimeError):
                clresp.return_code()

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

