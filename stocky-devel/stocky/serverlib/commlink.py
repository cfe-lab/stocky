"""Define a bluetooth communication link class for the TLS ASCII protocol.
"""

import typing
import serial

import serverlib.qai_helper as qai_helper
from webclient.commonmsg import CommonMSG

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

hextab = dict([(chr(ord('0') + i), i) for i in range(0, 10)] +
              [(chr(ord('A') + i), i+10) for i in range(0, 6)])


def HexStrtoStr(instr: str) -> str:
    """Convert a string of hex characters into legible characters.

    Depending on the RFID label being read, and the settings of the RFID reader,
    we can receive a string containing hexadecimal characters
    representing ASCII chars from the RFID reader when reading
    RFID labels.
    Here, convert these into a string of alphanumeric characters suitable
    for human consumption.
    For example, the received string '4348454D3130303030000000' is coded as::

      '43 48 45 4D 31 30 30 30 30 00 00 00'
        C  H  E  M  1  0  0  0  0

    where, for example, hexadecimal 43 is the ASCII character 'C'.
    Note that this conversion is only considered successful if the leading
    decoded character is 'human readable' , i.e. either a lower or uppercase letter or
    a numeral.
    If the conversion fails, return the original string.

    Args:
       instr: the raw string read from the RFID reader.

    Returns:
       The modified string upon successful conversion, otherwise
       the original string.
    """
    if len(instr) % 2 == 1 or len(instr) == 0:
        return instr
    # strlst: list of strings of length two representing hex numbers.
    strlst = [instr[i:i+2] for i in range(0, len(instr), 2)]
    # numlst: list of integers. if this fails, give up, as we do not have Hex numbers
    try:
        numlst = [hextab[hexstr[0]] * 16 + hextab[hexstr[1]] for hexstr in strlst]
    except KeyError:
        return instr
    # NOTE: also return the original string if the leading char is not a 'reasonable' ASCII
    # char.
    testchar = chr(numlst[0])
    charpass = 'A' <= testchar <= 'Z' or 'a' <= testchar <= 'z' or '1' <= testchar <= '9'
    # NOTE: the string can have multiple trailing zeros...
    return ''.join([chr(num) for num in numlst if num != 0]) if charpass else instr


class CLResponse:
    """ A class that contains the data that was sent from the RFID reader
    in response to a TLS command.

    Arguments:
       rl: a list containing the response from the RFID reader.
          if rl is None, this means that communication with the RFID reader timed out.
          if rl is am empty list, this means there was a protocol error during communication.
    """
    def __init__(self, rl: typing.Optional[ResponseList]) -> None:
        if rl is None:
            self.rl = None
            self._mydct: typing.Dict[str, StringList] = {}
            self._cdict = None
        else:
            self.rl = CLResponse._hexify(rl)
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

    @staticmethod
    def _hexify(rl: ResponseList) -> ResponseList:
        return [(EP_VAL, HexStrtoStr(tt[1])) if tt[0] == EP_VAL else tt for tt in rl]

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
        if self.rl is None:
            return BaseCommLink.RC_TIMEOUT
        if len(self.rl) == 0:
            return BaseCommLink.RC_FAULTY
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
    """A low-level communication link class that communicates with an RFID reader
    over a serial connection."""
    # Return codes of the RFID reader, see _tlsretcode_dct
    RC_OK = 0
    RC_FAULTY = 1
    RC_TIMEOUT = 2

    RC_NO_TAGS = 5
    RC_NO_BARCODE = 6

    DCT_START_CHAR = 'A'
    DCT_STOP_CHAR = 'B'

    COMMENT_ID = 'CMT'
    MSGNUM_ID = 'MSG'

    def __init__(self, cfgdct: dict) -> None:
        """Maintain a communication channel to an RFID device.

        Information needed to open such a channel will be extracted from
        the cfgdct.

        Args:
           cfgdct: This is the dict read from the server configuration file.
        """
        self.cfgdct = cfgdct
        self.logger = cfgdct['logger']
        # we keep track of command numbers.
        self._cmdnum = 0
        self.mydev = self.open_device()
        self._idstr: typing.Optional[str] = None

    def open_device(self) -> typing.Any:
        # NOTE: we do not raise an notimplemented exception here, because otherwise
        # we would not be able to instantiate a BaseCommLink.
        self.logger.warning('BaseCommLink.opendevice() called, which should not happen')
        return None

    def _close_device(self) -> None:
        pass

    def HandleStateChange(self, is_online: bool) -> None:
        """This routine is called when the BT link has changed...
        set out internal state accordingly.
        """
        if is_online:
            self.mydev = self.open_device()
            self._idstr = None
        else:
            self._close_device()
            self.mydev = None

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
                                qai_helper.tojson(d),
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
        return qai_helper.safe_fromjson(bytes(dict_str, 'utf-8'))

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

    def send_cmd(self, cmdstr: str, comment: str = None) -> None:
        """Send a string to the device as a command.
        The call returns as soon as the cmdstr data has been written.
        """
        commdct = {BaseCommLink.MSGNUM_ID: str(self._cmdnum), BaseCommLink.COMMENT_ID: comment}
        cmdstr += BaseCommLink.encode_comment_dict(commdct)
        self.raw_send_cmd(cmdstr)
        self._cmdnum += 1

    def _filterbyte(self) -> typing.Optional[bytes]:
        """Filter unwanted bytes from the RFID reader.

        Every now and again, the RFID reader sends us strings of bytes of
        0x00 and 0xff which cannot be translated into ASCII.
        As far as I know, we don't need these, so just filter them out here.
        Furthermore, we sometimes encounter a SerialException, so just catch this
        and treat it the same as a timeout.

        Returns:
           The required byte, or None if a timeout occurred on reading.
        """
        mydev = self.mydev
        doread = True
        skipset = frozenset([b'\xff', b'\x00'])
        while doread:
            try:
                b = mydev.read(size=1)
            except serial.serialutil.SerialException as e:
                self.logger.error("error reading from serial device: {}".format(str(e)))
                # same as a timeout...
                b = ""
            # print(" b: '{}'".format(b))
            if len(b) == 0:
                # time out occurred
                b = None
                doread = False
            else:
                doread = (b in skipset)
        return b

    def _str_readline(self) -> typing.Optional[str]:
        """Read a CR-LF-terminated string from the serial device.

        Read bytes (not strings) from the serial device until we hit
        a (CR, LF) then collect the bytes together into a line and return as a string.

        Returns:
           A string or None if a tim out occurred on reading.

        Raises:
            RuntimeError: if a CR character is read without a following LF character, or
                if conversion into a utf-8 string fails.
        """
        retbytes, doread = b'', True
        while doread:
            newbyte = self._filterbyte()
            # print("newbyte: {}".format(newbyte))
            if newbyte is None:
                return None
            if newbyte != byteCR:
                retbytes += newbyte
            else:
                newbyte = self._filterbyte()
                if newbyte != byteLF:
                    self.logger.error("rd: internal error 1")
                    raise RuntimeError('protocol error')
                doread = False
        try:
            retstr = str(retbytes, 'utf-8')
        except UnicodeDecodeError as e:
            raise RuntimeError("bytes '{}': {}".format(retbytes, e))
        return retstr

    def raw_send_cmd(self, cmdstr: str) -> None:
        """Send a string to the device as a command.
        The call returns as soon as the cmdstr data has been written.

        Arguments:
           cmdstr: the string to write to the device
        Raises:
           RuntimeError: is raised if something goes wrong.
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
            msg = "write failed '{}'".format(e)
            self.logger.error(msg)
            raise RuntimeError(msg)

    def raw_read_response(self) -> CLResponse:
        """Read a sequence of response tuples from the device.

        This code blocks until a terminating response tuple is returned, i.e.
        either an OK:<CRLF><CRLF> or an ER:nnn<CRLF><CRLF>, or until
        an error occurs.

        Errors can be of two main types:
        a) no response is received from the reader, in which case the
           connection will time out.
        b) a response that cannot be deciphered (unknown characters) is returned.
        In either case, the generated CLResponse will reflect these errors.
        Returns:
           The response is packed up into a CLResponse instance and returned.
        """
        rlst: typing.Optional[typing.List[ResponseTuple]] = []
        done = False
        while not done:
            try:
                cur_line = self._str_readline()
            except RuntimeError as e:
                self.logger.error("readline failed '{}'".format(e))
                cur_line = ""
            if cur_line is None:
                # time out
                rlst = None
                done = True
            elif len(cur_line) > 0:
                print("rr '{}' ({})".format(cur_line, len(cur_line)))
                resp_tup = BaseCommLink._line_2_resptup(cur_line)
                if resp_tup is not None:
                    rlst.append(resp_tup)
                else:
                    self.logger.error("line_2_resptup failed '{}'".format(cur_line))
            else:
                # we have reached a 'terminal' message (OK or ER)
                done = True
        self.logger.debug("raw_read_response got {}...".format(rlst))
        return CLResponse(rlst)

    def is_alive(self) -> bool:
        return self.mydev is not None

    def id_string(self) -> str:
        raise NotImplementedError("id_string not defined")

    def _blocking_cmd(self, cmdstr: str,
                      comment: str = None) -> CLResponse:
        """Send a command string to the reader, returning its list of response strings."""
        print("_blocking_cmd 1")
        try:
            self.send_cmd(cmdstr, comment)
        except RuntimeError:
            # write failed despite the device being open: a time-out problem
            print("write failed.. timeout")
            return CLResponse(None)
        print("_blocking_cmd 2")
        res = self.raw_read_response()
        print("_blocking_cmd 3")
        return res


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
    """Communicate with the RFID reader via a serial device (i.e. USB or Bluetooth).
    The name of the device to open  (typically something like '/dev/rfcomm0')
    is taken from the server configuration file.
    """

    def open_device(self) -> typing.Any:
        """Try to open a device for IO with the RFID scanner.

        The exact device to open depends on the configuration dict cfgdct.
        A typical name for this device would be /dev/rfcomm0.

        Returns:
           The device opened, or None if this fails.
        """
        cfgdct = self.cfgdct
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
        except Exception:
            self.logger.error("commlink failed to open device '{}' to RFID Reader '{}'".format(devname))
            myser = None
        self.logger.debug("serial commlink '{}' OK".format(devname))
        return myser

    def _close_device(self) -> None:
        if self.mydev is not None:
            self.mydev.close()

    def _is_responsive(self) -> bool:
        """Return := 'the RFID reader is responding to commands'"""
        cl_resp = self._blocking_cmd('.vr')
        retcode = cl_resp.return_code()
        return retcode != BaseCommLink.RC_TIMEOUT

    def get_RFID_state(self) -> int:
        if self.is_alive():
            if self._is_responsive():
                return CommonMSG.RFID_ON
            else:
                return CommonMSG.RFID_TIMEOUT
        return CommonMSG.RFID_OFF

    def id_string(self) -> str:
        """Determine a string showing information about the connected RFID reader

        Returns:
           A string describing the RFID reader if the connection is alive.
           If the connection (serial device) is not active, or the connection
           blocks (timeout), then this is reported instead."""
        if self._idstr is None:
            if self.is_alive():
                cl_resp = self._blocking_cmd('.vr')
                self.logger.debug("ID_STRING RESP: {}".format(cl_resp))
                retcode = cl_resp.return_code()
                if retcode == BaseCommLink.RC_TIMEOUT:
                    self._idstr = "ID string cannot be determined: commlink timed out"
                elif retcode == BaseCommLink.RC_FAULTY:
                    self._idstr = "ID string cannot be determined: response is faulty"
                else:
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
            else:
                self._idstr = "ID string cannot be determined: commlink is down"
        return self._idstr
