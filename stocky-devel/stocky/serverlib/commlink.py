
# define a bluetooth communication link class for the TLS ASCII protocol

import typing
import serial

import serverlib.QAILib as QAILib

OK_RESP = 'OK'
ER_RESP = 'ER'
RI_VAL = 'RI'
ME_VAL = 'ME'
CS_VAL = 'CS'
EP_VAL = 'EP'

resp_code_lst = ['AB', 'AC', 'AE', 'AS', 'BA', 'BC', 'BP', 'BR', 'CH', 'CR', 'DA', 'DP',
                 'DT', 'EA', 'EB', 'FN', 'IA', 'IX', 'KS', 'LB', 'LE', 'LL', 'LK', 'LS',
                 'MF', 'QT', 'PC', 'PR', 'PV', 'RB', 'RD', 'RF', 'RS', 'SP', 'BV',
                 'SR', 'SW', 'TD', 'TM', 'UB', 'UF', 'US', 'WW', OK_RESP, ER_RESP, RI_VAL,
                 ME_VAL, CS_VAL, EP_VAL]

resp_code_set = frozenset(resp_code_lst)

ResponseTuple = typing.Tuple[str, str]
ResponseList = typing.List[ResponseTuple]

ResponseDict = typing.Dict[str, str]
StringList = typing.List[str]


command_lst = ['al', 'ab', 'bc', 'bl', 'bt', 'da', 'dp', 'ea', 'ec',
               'fd', 'hc', 'hd', 'hs', 'iv', 'ki', 'lk', 'lo', 'mt',
               'pd', 'ps', 'ra', 'rd', 'rl', 'sa', 'sl', 'sp', 'sr',
               'ss', 'st', 'tm', 'ts', 'vr', 'wa', 'wr', 'ws']
command_set = frozenset(command_lst)


byteCR = b'\r'
byteLF = b'\n'

byteCRLF = b"\r\n"

OK_RESP_TUPLE = (OK_RESP, '')

OK_RESP_LIST = [('OK', '')]

# For the error codes, see the document 'TLS ASCII protocol 2.5 rev B', page 14.
# We include an error code zero here to indicate a success.
TLSRetCode = int

# RSSI value: return signal strength in dBm
# (a negative value, bigger is closer. E.g. -40 is nearer than -75)
RSSI = int


class CLResponse:
    def __init__(self, rl: ResponseList) -> None:
        self.rl = rl
        dd: typing.Dict[str, StringList] = {}
        self._mydct = dd
        for resp_code, msg in self.rl:
            dd.setdefault(resp_code, []).append(msg)
        # now, from the CS field, extract the comment dict
        cdict = None
        cslst = dd.get(CS_VAL, None)
        if cslst is not None:
            if len(cslst) != 1:
                raise RuntimeError("CS field must be present exactly once")
            cs_string = cslst[0]
            cdict = BaseCommLink.extract_comment_dict(cs_string)
        self._cdict = cdict

    def __getitem__(self, respcode: str) -> typing.Optional[StringList]:
        """Return a list with only those response codes equal to respcode.
        Return None if no entries of type respcode are found.
        NOTE: this routine overwrites the [] operator for this class.
        """
        assert respcode in resp_code_set, "illegal respcode"
        # print("looking for '{}', have {}".format(respcode, self._mydct))
        return self._mydct.get(respcode, None)

    @staticmethod
    def _check_get_int_val(r: ResponseTuple, resp_code: str) -> int:
        """Extract an integer value from the send part of r.
        Raise an exception if it does not contain an integer string.
        """
        cmd, arg = r
        if cmd == resp_code:
            # convert the arg string into an int
            try:
                ii = int(arg)
            except ValueError:
                raise RuntimeError("return_code: failed to convert to int")
            return ii
        else:
            raise RuntimeError("return_code: unexpected {}, expected {}".format(cmd, resp_code))

    def return_code(self) -> TLSRetCode:
        """Return a return code as an integer from a ResponseList received
        from the TLS reader.
        For the error codes, see the document 'TLS ASCII protocol 2.5 rev B', page 14.
        We include an error code zero here to indicate a success.
        """
        if len(self.rl) == 0:
            raise RuntimeError("return code from empty list")
        last_tup = self.rl[-1]
        if last_tup == OK_RESP_TUPLE:
            return BaseCommLink.RC_OK
        else:
            return CLResponse._check_get_int_val(last_tup, ER_RESP)

    def _return_message(self) -> typing.Optional[str]:
        """Return a message sent from the RFID reader in the ME: field of the
        ResponseList. Return None if there is no message."""
        rlst = self.__getitem__(ME_VAL)
        if rlst is None or len(rlst) != 1:
            return None
        else:
            return rlst[0]

    def get_comment_dct(self) -> typing.Optional[dict]:
        return self._cdict

    def __str__(self):
        return "CLResponse: '{}' comment: {}".format(self.rl, self._cdict)


class BaseCommLink:
    # Return codes of the RFID reader, see _tlsretcode_dct
    RC_OK = 0

    RC_NO_TAGS = 5
    RC_NO_BARCODE = 6

    DCT_START_CHAR = 'A'
    DCT_STOP_CHAR = 'B'

    COMMENT_ID = 'CMT'
    MSGNUM_ID = 'MSG'

    def __init__(self, cfgdct: dict) -> None:
        """Open a communication channel defined by its id.
        Information needed to open such a channel will be extracted from
        the cfgdct. This is the dict resulting from the server configuration file.
        """
        self.cfgdct = cfgdct
        self.logger = cfgdct['logger']
        # we keep track of command numbers.
        self._cmdnum = 0

    @staticmethod
    def _line_2_resptup(l: str) -> typing.Optional[ResponseTuple]:
        if len(l) < 3:
            return None
        ret_code = l[:2]
        colon = l[2]
        rest = l[3:].strip()
        if ret_code not in resp_code_set or colon != ':':
            return None
        return (ret_code, rest)

    @staticmethod
    def encode_comment_dict(d: dict) -> str:
        """Convert a dict into a json string suitable for sending
        to the RFID reader as a comment
        """
        # NOTE: the leading space in the format string is required
        return " {}{}{}".format(BaseCommLink.DCT_START_CHAR,
                                QAILib.tojson(d),
                                BaseCommLink.DCT_STOP_CHAR)

    @staticmethod
    def extract_comment_dict(s: str) -> typing.Optional[dict]:
        """Extract a previously encoded comment dict from a string.
        Return None if the string does not have the required delimiters '#' and '@'
        """
        hash_ndx = s.find(BaseCommLink.DCT_START_CHAR)
        ampers_ndx = s.find(BaseCommLink.DCT_STOP_CHAR)
        if hash_ndx == -1 or ampers_ndx == -1:
            return None
        dict_str = s[hash_ndx+1:ampers_ndx]
        return QAILib.safe_fromjson(bytes(dict_str, 'utf-8'))

    @staticmethod
    def RC_string(ret_code: TLSRetCode) -> str:
        """Convert the TLS reader return code into a descriptive string.
        For the error codes, see the document 'TLS ASCII protocol 2.5 rev B', page 14.
        We include an error code zero here to indicate a success.
        """
        ret_str = _tlsretcode_dct.get(ret_code, None)
        if ret_str is None:
            raise RuntimeError("unknown error code {}".format(ret_code))
        return ret_str

    def send_cmd(self, cmdstr: str, comment: str=None) -> None:
        """Send a string to the device as a command.
        The call returns as soon as the cmdstr data has been written.
        """
        commdct = {BaseCommLink.MSGNUM_ID: str(self._cmdnum), BaseCommLink.COMMENT_ID: comment}
        cmdstr += BaseCommLink.encode_comment_dict(commdct)
        self.raw_send_cmd(cmdstr)
        self._cmdnum += 1

    def raw_send_cmd(self, cmdstr: str) -> None:
        """Send a string to the device as a command.
        The call returns as soon as the cmdstr data has been written.
        """
        raise NotImplementedError("send not defined")

    def raw_read_response(self) -> CLResponse:
        """Read a sequence of response tuples from the device.
        This code blocks until a terminating response tuple is returned, i.e.
        either an OK:<CRLF><CRLF> or an ER:nnn<CRLF><CRLF>.
        The response is packed up into a CLResponse instance and returned.
        """
        raise NotImplementedError("read not defined")

    def is_alive(self, doquick: bool=True) -> bool:
        raise NotImplementedError("is_alive not defined")

    def id_string(self) -> str:
        raise NotImplementedError("id_string not defined")

    def _blocking_cmd(self, cmdstr: str,
                      comment: str=None) -> CLResponse:
        """Send a command string to the reader, returning its list of response strings."""
        self.send_cmd(cmdstr, comment)
        return self.raw_read_response()


_tlsretcode_dct = {0: 'No Error',
                   1: 'Syntax Error',
                   2: 'Parameter not supported',
                   3: 'Action not enabled',
                   4: 'Command not supported by hardware',
                   BaseCommLink.RC_NO_TAGS: 'No transponder found',
                   BaseCommLink.RC_NO_BARCODE: 'No Barcode found',
                   7: 'Parameter configuration invalid',
                   8: 'Antenna/Radio Error (Wrong region of Antenna/Radio not fitted)',
                   9: 'Battery level too low',
                   10: 'Scanner not ready',
                   11: 'Command not supported on interface',
                   12: 'Command not supported from Autorun file',
                   13: 'Write Failure',
                   14: 'Switch already in use',
                   15: 'Command Aborted',
                   16: 'Lock Failure',
                   17: 'Bluetooth Error',
                   18: 'Licence Key is not Blank',
                   255: 'System Error'}


class SerialCommLink(BaseCommLink):
    """Communicate with the RFID reader via a serial device (i.e. USB or Bluetooth)"""

    def __init__(self, cfgdct: dict) -> None:
        super().__init__(cfgdct)
        devname = cfgdct['RFID_READER_DEVNAME']
        self.logger.debug("commlink opening '{}'".format(devname))
        try:
            myser = serial.Serial(devname,
                                  baudrate=19200,
                                  parity='N')
            self.logger.debug('SerialCommlink: opening serial device.')
        except IOError as e:
            self.logger.error("commlink failed to open device '{}' to RFID Reader '{}'".format(devname, e))
            myser = None
        except Exception as e:
            self.logger.error("commlink failed to open device '{}' to RFID Reader '{}'".format(devname))
            myser = None
        self.mydev = myser
        self.logger.debug("serial commlink '{}' OK".format(devname))
        self._idstr: typing.Optional[str] = None

    def raw_send_cmd(self, cmdstr: str) -> None:
        """Send a string to the device as a command.
        The call returns as soon as the cmdstr data has been written.
        An exception is raised if something goes wrong.
        """
        if self.mydev is None:
            msg = 'CL: raw_send_cmd: Device is not alive!'
            self.logger.error(msg)
            raise RuntimeError(msg)
        try:
            self.logger.debug("CL: writing '{}'".format(cmdstr))
            self.mydev.write(bytes(cmdstr, 'utf-8') + byteCRLF)
            self.mydev.flush()
        except Exception as e:
            self.logger.error("write failed '{}'".format(e))
            raise

    def filterbyte(self) -> bytes:
        """Every now and again, the RFID reader sends us bytes 0x00 and 0xff which cannot
        be translated into ASCII.
        As far as I know, we don't need these, so just filter them out here.
        """
        mydev = self.mydev
        doread = True
        skipset = frozenset([b'\xff', b'\x00'])
        while doread:
            b = mydev.read(size=1)
            doread = (b in skipset)
        return b

    def _str_readline(self) -> str:
        """Read bytes (not strings) from the serial device until we hit
        a (CR, LF) then collect together into a line and return as a string"""
        retbytes, doread = b'', True
        while doread:
            newbytes = self.filterbyte()
            if newbytes != byteCR:
                retbytes += newbytes
            else:
                newbytes = self.filterbyte()
                if newbytes != byteLF:
                    self.logger.error("rd: internal error 1")
                    raise RuntimeError('protocol error')
                doread = False
        try:
            retstr = str(retbytes, 'utf-8')
        except UnicodeDecodeError as e:
            raise RuntimeError("bytes '{}': {}".format(retbytes, e))
        return retstr

    def raw_read_response(self) -> CLResponse:
        """Read a sequence of response tuples from the device.
        Return a CLResponse instance.
        """
        self.logger.debug("raw_read...")
        rlst, done = [], False
        while not done:
            try:
                cur_line = self._str_readline()
            except Exception as e:
                self.logger.error("readline failed '{}'".format(e))
                raise
            self.logger.debug("rr '{}' ({})".format(cur_line, len(cur_line)))
            if len(cur_line) > 0:
                resp_tup = BaseCommLink._line_2_resptup(cur_line)
                if resp_tup is not None:
                    rlst.append(resp_tup)
                else:
                    self.logger.error("line_2_resptup failed '{}'".format(cur_line))
            else:
                # we have reached a 'terminal' message (OK or ER)
                done = True        # --
        self.logger.debug("raw_read got {}...".format(rlst))
        return CLResponse(rlst)

    def is_alive(self, doquick: bool=True) -> bool:
        return self.mydev is not None

    def id_string(self) -> str:
        if self._idstr is None:
            cl_resp = self._blocking_cmd('.vr')
            self.logger.debug("ID_STRING RESP: {}".format(cl_resp))
            klst = [('Manufacturer', 'MF'),
                    ('Unit serial number', 'US'),
                    ('Unit firmware version', 'UF'),
                    ('Unit bootloader version', 'UB'),
                    ('Antenna serial number', 'AS'),
                    ('Radio serial number', 'RS'),
                    ('Radio firmware version', 'RF'),
                    ('Radio bootloader version', 'RB'),
                    ('BT address', 'BA'),
                    ('Protocol version', 'PV')]
            self._idstr = ", ".join(["{}: {}".format(title, cl_resp[k]) for title, k in klst])
        return self._idstr


class DummyCommLink(BaseCommLink):
    """A dummy commlink used for testing"""

    def __init__(self, cfgdct: dict) -> None:
        super().__init__(cfgdct)
        self.resplst: typing.List[str] = []

    def is_alive(self, doquick: bool=True) -> bool:
        return True

    def id_string(self) -> str:
        return "DummyCommLink"

    @staticmethod
    def get_cmd_from_str(cmdstr: str) -> typing.Tuple[str, dict]:
        # split off any comment dict if it exists...
        comm_ndx = cmdstr.find(BaseCommLink.DCT_START_CHAR)
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
        if cc not in command_set:
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

    def raw_read_response(self) -> CLResponse:
        rlst = []
        done = len(self.resplst) == 0
        while not done:
            cur_line = self.resplst.pop(0).strip()
            if len(cur_line) > 0:
                resp_tup = BaseCommLink._line_2_resptup(cur_line)
                if resp_tup is not None:
                    rlst.append(resp_tup)
                else:
                    self.logger.error("line_2_resptup failed '{}'".format(cur_line))
            else:
                # we have reached a 'terminal' message (OK or ER)
                done = True
            done = len(self.resplst) == 0
        # --
        return CLResponse(rlst)
