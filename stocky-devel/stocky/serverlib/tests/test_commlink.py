import typing
import pytest
import logging
import serial

import webclient.commonmsg as commonmsg
import serverlib.commlink as commlink


class dummyserialdevice:
    """A dummy serial device that is loaded with content which can then
    be accessed in tests by issuing reads"""

    def __init__(self, cont: bytes = b'') -> None:
        assert isinstance(cont, bytes), "expected bytes"
        self.cont = cont
        self.pos = 0
        self.doraise = False
        self._isclosed = False

    def read(self, size: int = 1) -> bytes:
        assert size == 1, 'only support size = 1'
        assert not self._isclosed, "device is closed"
        if self.pos < len(self.cont):
            retbyte = self.cont[self.pos:self.pos+1]
            self.pos += 1
            assert isinstance(retbyte, bytes), 'read returning non-byte'
            return retbyte
        else:
            raise RuntimeError('EOF reached')

    def write(self, b: bytes) -> None:
        assert isinstance(b, bytes), 'write wants bytes!'
        assert not self._isclosed, "device is closed"
        self.cont += b

    def flush(self) -> None:
        assert not self._isclosed, "device is closed"
        if self.doraise:
            raise RuntimeError('Raise on Flush')

    def get_cont(self) -> bytes:
        return self.cont

    def raise_on_flush(self, on: bool) -> None:
        self.doraise = on

    def close(self) -> None:
        self._isclosed = True


class timeout_dummyserialdevice(dummyserialdevice):
    """A dummy serial device that always times out on reads"""

    def read(self, size: int = 1) -> bytes:
        assert size == 1, 'only support size = 1'
        return b''


class exception_dummyserialdevice(dummyserialdevice):
    """A dummy serial device that raises an exception on reads"""

    def __init__(self, cont: bytes = b'') -> None:
        super().__init__(cont)
        self.num_exceptions = 0

    def read(self, size: int = 1) -> bytes:
        print("RAISING SerialException")
        self.num_exceptions += 1
        raise serial.serialutil.SerialException('test dummy exception')

    def num_exception_calls(self) -> int:
        return self.num_exceptions


class DummySerialCommLink(commlink.SerialCommLink):

    def open_device(self) -> typing.Any:
        return dummyserialdevice(b'bla')


class TimeoutDummySerialCommLink(commlink.SerialCommLink):

    def open_device(self) -> typing.Any:
        return timeout_dummyserialdevice(b'bla')


class ExceptionDummySerialCommLink(commlink.SerialCommLink):

    def open_device(self) -> typing.Any:
        return exception_dummyserialdevice(b'bla')


class DummyCommLink(commlink.BaseCommLink):
    """A dummy commlink used for testing.
    This class will pretend to be a serial device, but actually
    sanity check the commands sent, then also generate some really simple
    answer codes.
    """

    def __init__(self, cfgdct: dict) -> None:
        super().__init__(cfgdct)
        self.resplst: typing.List[str] = []

    def _is_alive(self, doquick: bool = True) -> bool:
        return True

    def id_string(self) -> str:
        return "DummyCommLink"

    def open_device(self) -> typing.Any:
        return None

    @staticmethod
    def get_cmd_from_str(cmdstr: str) -> typing.Tuple[str, dict]:
        # split off any comment dict if it exists...
        comm_ndx = cmdstr.find(commlink.BaseCommLink.DCT_START_CHAR)
        if comm_ndx != -1:
            cmdstr = cmdstr[:comm_ndx-1]
        if len(cmdstr) < 3:
            raise RuntimeError("cmdstr too short")
        cmdargs = cmdstr.split()
        if len(cmdargs) == 0:
            raise RuntimeError("cmdargs is 0")
        cmd = cmdargs[0]
        if cmd[0] != '.':
            raise RuntimeError("cmdstr must start with a period")
        cc = cmd[1:]
        if cc not in commlink.command_set:
            raise RuntimeError("unknown command '{}'".format(cmd))
        optdct = {}
        i, n = 1, len(cmdargs)
        while i < n:
            opt = cmdargs[i]
            if opt[0] == '-':
                optkey = opt[1:]
                if i+1 < n and cmdargs[i+1][0] != '-':
                    i += 1
                    optval = cmdargs[i]
                else:
                    optval = ''
                optdct[optkey] = optval
            else:
                raise RuntimeError('syntax error')
            i += 1
        return cc, optdct

    def raw_send_cmd(self, cmdstr: str) -> None:
        """Perform a sanity check of cmdstr and save it for later.
        Raise an exception if there is an error in the command.
        Also, for testing purposes, pretend to return some actual values depending
        on the command issued.
        """
        cc, optdct = DummyCommLink.get_cmd_from_str(cmdstr)
        self.resplst.append('CS: {}'.format(cmdstr))
        if cc == 'iv' and 'x' not in optdct:
            self.resplst.append('RI: -40')
        self.resplst.extend(['OK:', ''])

    def raw_read_response(self) -> commlink.CLResponse:
        rlst = []
        done = len(self.resplst) == 0
        while not done:
            cur_line = self.resplst.pop(0).strip()
            if len(cur_line) > 0:
                resp_tup = commlink.BaseCommLink._line_2_resptup(cur_line)
                if resp_tup is not None:
                    rlst.append(resp_tup)
                else:
                    self.logger.error("line_2_resptup failed '{}'".format(cur_line))
            else:
                # we have reached a 'terminal' message (OK or ER)
                done = True
            done = len(self.resplst) == 0
        # --
        return commlink.CLResponse(rlst)


BaseCommLinkClass = commlink.BaseCommLink
DummyCommLinkClass = DummyCommLink

CommLinkClass = DummyCommLink


class Test_exception_commlink:
    """Test the proper handling of serial device raises a SerialException."""

    def setup_method(self) -> None:
        self.logger = logging.Logger("testing")
        cfgdct = {'logger': self.logger}
        self.dscl = ExceptionDummySerialCommLink(cfgdct)

    def test_readexception01(self) -> None:
        """raw_read_response() should return a time out code
        when a serial device raises a serial.serialutil.SerialException on read."""
        assert self.dscl.mydev.num_exception_calls() == 0, "zero exception expected"
        resp = self.dscl.raw_read_response()
        assert self.dscl.mydev.num_exception_calls() == 1, "one exception expected"
        print("resp is '{}'".format(resp))
        assert resp is not None, "CLResp expected"
        retcode = resp.return_code()
        assert retcode == commlink.BaseCommLink.RC_TIMEOUT, "timeout expected"

    def test_is_responsive01(self) -> None:
        """_is_responsive() should return False for a dummy device."""
        res = self.dscl._is_responsive()
        assert isinstance(res, bool), "bool expected"
        assert not res, "expected False"

    def test_get_RFID_state(self) -> None:
        """get_RFID_state() should return RFID_TIMEOUT and get_info_dct() should return None
        when using a dummy serial device."""
        res = self.dscl.get_RFID_state()
        assert isinstance(res, int), "int expected"
        print("RES {}".format(res))
        assert res == commonmsg.CommonMSG.RFID_TIMEOUT, "expected False"
        idct = self.dscl.get_info_dct()
        print("RES {}".format(idct))
        assert idct is None, "None expected"


class Test_timeout_commlink:
    """Test the proper handling of serial device time outs."""

    def setup_method(self) -> None:
        self.logger = logging.Logger("testing")
        cfgdct = {'logger': self.logger}
        self.cl = CommLinkClass(cfgdct)
        if not self.cl._is_alive():
            print("Test cannot be performed: commlink is not alive")
        idstr = self.cl.id_string()
        print("commlink is alive. Ident is {}".format(idstr))
        self.dscl = TimeoutDummySerialCommLink(cfgdct)

    def test_read_TO_01(self) -> None:
        """_str_readline() should return None if the serial device is offline."""
        retval = self.dscl._str_readline()
        assert retval is None, "None expected"

    def test_rawread01(self) -> None:
        """raw_read_response() should return the expected class and return code."""
        clresp = self.dscl.raw_read_response()
        assert isinstance(clresp, commlink.CLResponse), "clresponse expected"
        retcode = clresp.return_code()
        assert retcode == commlink.BaseCommLink.RC_TIMEOUT, "time out expected"

    def test_clresp01(self) -> None:
        """A return code of an CLResponse instance with an empty response list
        or faulty message returns RC_FAULTY."""
        for bad_lst in [[], ['bl'], [('UB', '1')]]:
            print("BADLST: '{}'".format(bad_lst))
            clresp = commlink.CLResponse(bad_lst)
            retcode = clresp.return_code()
            assert retcode == commlink.BaseCommLink.RC_FAULTY, "RC faulty expected"

    def test_handlestatechange01(self) -> None:
        """dscl._is_alive() and id_string() should return expected values
        after HandleStateChange(True)"""
        self.dscl.HandleStateChange(True)
        is_alive = self.dscl._is_alive()
        assert isinstance(is_alive, bool), "bool expected"
        assert is_alive, "commlink should be alive"
        id_expected = "ID string cannot be determined: commlink timed out"
        idstr = self.dscl.id_string()
        print(" got idstr: {}".format(idstr))
        assert idstr == id_expected, "unexpected id string"

    def test_handlestatechange02(self) -> None:
        """dscl._is_alive() and id_string() should return expected values
        after HandleStateChange(False)"""
        self.dscl.HandleStateChange(False)
        is_alive = self.dscl._is_alive()
        assert isinstance(is_alive, bool), "bool expected"
        assert not is_alive, "commlink should be alive"
        id_expected = "ID string cannot be determined: commlink is down"
        idstr = self.dscl.id_string()
        print(" got idstr: {}".format(idstr))
        assert idstr == id_expected, "unexpected id string"


class Test_commlink:

    def setup_method(self) -> None:
        self.logger = logging.Logger("testing")
        cfgdct = {'logger': self.logger}
        self.cl = CommLinkClass(cfgdct)
        if not self.cl._is_alive():
            print("Test cannot be performed: commlink is not alive")
        idstr = self.cl.id_string()
        print("commlink is alive. Ident is {}".format(idstr))
        self.dscl = DummySerialCommLink(cfgdct)

    def test_idstr01(self) -> None:
        """commlink.id_string() should return an expected error string
        when the id string cannot be determined."""
        exp_id = "ID string cannot be determined: response is faulty"
        idstr = self.dscl.id_string()
        print("idstr: {}".format(idstr))
        assert idstr == exp_id, "unexpected idstring"

    def test_Hextostr(self):
        """commlink.HexStrtoStr must return the expected string on various input.
        """
        lverb = False
        for instr, exp_outstr in [('4348454D3130303030000000', "CHEM10000", ),
                                  ('BLA', 'BLA'),
                                  ('BLAA', 'BLAA'),
                                  ('00FA01', '00FA01')]:
            gotstr = commlink.HexStrtoStr(instr)
            if lverb:
                print(" GOT {} --> {}".format(instr, gotstr))
            assert isinstance(gotstr, str), "string expected"
            if gotstr != exp_outstr:
                raise RuntimeError("input {} produced {}, expected {}".format(instr, gotstr, exp_outstr))
        # assert False, "force fail"

    def test_str_read01(self):
        """_str_readline must strip out unwanted characters."""
        cfgdct = {'logger': self.logger}
        dscl = DummySerialCommLink(cfgdct)
        dscl.mydev = dummyserialdevice(b'he\xffll\x00o' + commlink.byteCRLF)
        retval = dscl._str_readline()
        assert isinstance(retval, str), 'string expected'
        assert retval == 'hello', 'hello expected'
        # print('retval {}'.format(retval))
        # assert False, 'force fail'

    def test_str_read02(self):
        """_str_readline must raise an exception if a line is not properly terminated."""
        cfgdct = {'logger': self.logger}
        dscl = DummySerialCommLink(cfgdct)
        dscl.mydev = dummyserialdevice(b'he\xffll\x00o' + commlink.byteCR + commlink.byteCR)
        with pytest.raises(RuntimeError):
            dscl._str_readline()

    def test_str_read03(self):
        """_str_readline must raise an exception when it reads non-utf8 characters."""
        cfgdct = {'logger': self.logger}
        dscl = DummySerialCommLink(cfgdct)
        dscl.mydev = dummyserialdevice(b'he\xfell\x00o' + commlink.byteCRLF)
        with pytest.raises(RuntimeError):
            dscl._str_readline()

    def test_raw_send_cmd01(self):
        """
        raw_send_cmd() should raise a RuntimeError if the serial device (mydev) is None
        """
        cfgdct = {'logger': self.logger}
        dscl = DummySerialCommLink(cfgdct)
        with pytest.raises(RuntimeError):
            dscl.mydev = None
            dscl.raw_send_cmd('hello RFID')
        #
        ds = dscl.mydev = dummyserialdevice()
        teststr = 'hello RFID'
        dscl.raw_send_cmd(teststr)
        gotbytes = ds.get_cont()
        assert isinstance(gotbytes, bytes), 'expected bytes'
        # NOTE: the received string will have CRLF appended to it.
        gotstr = str(gotbytes, 'utf-8').strip()
        assert teststr == gotstr, 'unexpected string'

        # now switch on ds to raise an exception on flush
        ds.raise_on_flush(True)
        with pytest.raises(RuntimeError):
            dscl.raw_send_cmd(teststr)

    def test_raw_read_response01(self):
        """raw_read_response() should return a commlink.CLResponse instance.
        """
        cfgdct = {'logger': self.logger}
        dscl = DummySerialCommLink(cfgdct)
        testbytes = b"""CS: .iv'
        EP: 000000000000000000001242
        RI: -61
        OK:""" + commlink.byteCRLF + commlink.byteCRLF
        dscl.mydev = dummyserialdevice(testbytes)
        retval = dscl.raw_read_response()
        assert isinstance(retval, commlink.CLResponse), 'wrong type'
        # assert False, "force fail"

    def test_is_alive01(self):
        """_is_alive() should return expected values."""
        cfgdct = {'logger': self.logger}
        dscl = DummySerialCommLink(cfgdct)
        assert dscl._is_alive(), "expected true"
        dscl.mydev = None
        assert not dscl._is_alive(), "expected false"

    def test_baseCL_notimp(self):
        """BaseCommLinkClass should raise NotImplemented errors on certain
        methods."""
        b = BaseCommLinkClass({'logger': self.logger})
        for func in [lambda b: b.id_string()]:
            with pytest.raises(NotImplementedError):
                func(b)

    def test_baseCL_RC_string_legal(self):
        """Converting legal retcodes to a descriptive string using
        RC_string should succeed."""
        for retcode in commlink._tlsretcode_dct.keys():
            retstr = BaseCommLinkClass.RC_string(retcode)
            assert isinstance(retstr, str), "expected a string"

    def test_baseCL_RC_string_illegal(self):
        """Converting illegal retcodes to a descriptive string using
        RC_string should raise a RuntimeError."""
        """Convert illlegal retcodes"""
        for retcode in [-100, 50]:
            with pytest.raises(RuntimeError):
                BaseCommLinkClass.RC_string(retcode)

    def test_baseCL_comment_dct01(self):
        """BaseCommLinkClass.encode_comment_dict and
        BaseCommLinkClass.extract_comment_dict must operate as expected.
        """
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
        """Test the CLResponse class on a number of legit/ non legit
        RFID reader response strings."""
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

    def test_clresponse02(self) -> None:
        """Test CLResponse when the serial connection has timed
        out (return list is None)"""
        clresp = commlink.CLResponse(None)
        assert clresp is not None, "Failed to instantiate CLResponse"
        cslst = clresp["CS"]
        assert cslst is None, "Non expected"
        rc = clresp.return_code()
        assert rc == commlink.BaseCommLink.RC_TIMEOUT
        cmt_dct = clresp.get_comment_dct()
        assert cmt_dct is None, "expected None"

    def test_cl_return_message01(self) -> None:
        """Test behaviour of _return_message() on good and bad messages.
        """
        testy_lst = [([("ME", "hello")], "hello"),
                     ([("AA", "funny")], None)]
        for test_lst, resp_exp in testy_lst:
            clresp = commlink.CLResponse(test_lst)
            resp_got = clresp._return_message()
            assert resp_got == resp_exp, "unexpected RespTuple"

    def test_cl_return_code01(self):
        """Test return_code() on a number of valid/ invalid response messages."""
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
        """Issuing an invalid command should result in a time out condition."""
        ret = self.cl._blocking_cmd(".bla -p")
        assert isinstance(ret, commlink.CLResponse), "CLResponse expected"
        ret_code = ret.return_code()
        assert ret_code == commlink.BaseCommLink.RC_TIMEOUT
        # assert False, "force fail"

    def test_check_int_val01(self) -> None:
        """Calling CLResponse._check_get_int_val() with bad data should
        raise an exception."""
        # a) not an integer argument...
        cmd = commlink.ER_RESP
        arg = 'not an int'
        my_tup = (cmd, arg)
        with pytest.raises(RuntimeError):
            commlink.CLResponse._check_get_int_val(my_tup, commlink.ER_RESP)
        # b) not the expected command
        cmd = 'bla'
        arg = '100'
        my_tup = (cmd, arg)
        with pytest.raises(RuntimeError):
            commlink.CLResponse._check_get_int_val(my_tup, commlink.ER_RESP)
