

# define a bluetooth communication link class for the TLS ASCII protocol

import typing


OK_RESP = 'OK'
ER_RESP = 'ER'
RI_VAL = 'RI'

resp_code_lst = ['AB', 'AC', 'AE', 'AS', 'BA', 'BC', 'BP', 'BR', 'CH', 'CR', 'CS', 'DA', 'DP',
                 'DT', 'EA', 'EB', 'FN', 'IA', 'IX', 'KS', 'LB', 'LE', 'LL', 'LK', 'LS',
                 'ME', 'MF', 'QT', 'PC', 'PR', 'PV', 'RB', 'RD', 'RF', 'RS', 'SP',
                 'SR', 'SW', 'TD', 'TM', 'UB', 'UF', 'US', 'WW', OK_RESP, ER_RESP, RI_VAL]

resp_code_set = frozenset(resp_code_lst)

DEFAULT_TIMEOUT_SECS = 20

ResponseTuple = typing.Tuple[str, str]
ResponseList = typing.List[ResponseTuple]

command_lst = ['al', 'ab', 'bc', 'bl', 'bt', 'da', 'dp', 'ea', 'ec',
               'fd', 'hc', 'hd', 'hs', 'iv', 'ki', 'lk', 'lo', 'mt',
               'pd', 'ps', 'ra', 'rd', 'rl', 'sa', 'sl', 'sp', 'sr',
               'ss', 'st', 'tm', 'ts', 'vr', 'wa', 'wr', 'ws']
command_set = frozenset(command_lst)

CRLF = "\r\n"

OK_RESP_TUPLE = (OK_RESP, '')

OK_RESP_LIST = [('OK', '')]

# For the error codes, see the document 'TLS ASCII protocol 2.5 rev B', page 14.
# We include an error code zero here to indicate a success.
TLSRetCode = int

# RSSI value: return signal strength in dBm
# (a negative value, bigger is closer. E.g. -40 is nearer than -75)
RSSI = int

_tlsretcode_dct = {0: 'No Error',
                   1: 'Syntax Error',
                   2: 'Parameter not supported',
                   3: 'Action not enabled',
                   4: 'Command not supported by hardware',
                   5: 'No transponder found',
                   6: 'No Barcode found',
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


class BaseCommLink:
    RC_OK = 0

    def __init__(self, id: str) -> None:
        """Open a communication channel defined by its id."""
        self.id = id

    @staticmethod
    def _line_2_resptup(l: str) -> ResponseTuple:
        if len(l) < 3:
            return None
        ret_code = l[:2]
        colon = l[2]
        rest = l[3:].strip()
        if ret_code not in resp_code_set or colon != ':':
            return None
        return (ret_code, rest)

    def raw_send_cmd(self, cmdstr: str) -> None:
        """Send a string to the device as a command.
        The call returns as soon as the cmdstr data has been written.
        """
        raise NotImplementedError("send not defined")

    @staticmethod
    def _check_get_int_val(r: ResponseTuple, resp_code: str) -> int:
        """Extract an integer value from the send part of r.
        Raise an exception if it does not contain an integer string.
        """
        cmd, arg = r
        if cmd == resp_code:
            # convert the arg string into an int
            return int(arg)
        else:
            raise RuntimeError("return_code: unexpected {}, expected {}".format(cmd, resp_code))

    @staticmethod
    def return_code(l: ResponseList) -> TLSRetCode:
        """Return a return code as an integer from a ResponseList received
        from the TLS reader.
        For the error codes, see the document 'TLS ASCII protocol 2.5 rev B', page 14.
        We include an error code zero here to indicate a success.
        """
        if len(l) == 0:
            raise RuntimeError("return code from empty list")
        last_tup = l[-1]
        if last_tup == OK_RESP_TUPLE:
            return BaseCommLink.RC_OK
        else:
            return BaseCommLink._check_get_int_val(last_tup, ER_RESP)

    @staticmethod
    def _extract_response(l: ResponseList, respcode: str) -> ResponseList:
        """Return a list with only those response codes equal to respcode"""
        assert respcode in resp_code_set, "illegal respcode"
        return [t for t in l if t[0] == respcode]

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

    def raw_read_response(self, timeout_secs: int) -> ResponseList:
        """Read a sequence of response tuples from the device.
        This code blocks until a terminating response tuple is returned, i.e.
        either an OK:<CRLF><CRLF> or an ER:nnn<CRLF><CRLF> or
        until a timeout occurs.
        """
        raise NotImplementedError("read not defined")

    def is_alive(self, doquick: bool=True) -> bool:
        raise NotImplementedError("is_alive not defined")

    def id_string(self) -> str:
        raise NotImplementedError("id_string not defined")

    def execute_cmd(self, cmdstr: str, timeout_secs=DEFAULT_TIMEOUT_SECS) -> ResponseList:
        """ send a command string to the reader, returning its list of response strings."""
        self.raw_send_cmd(cmdstr)
        return self.raw_read_response(timeout_secs)

    def execute_is_ok(self, cmdstr: str, verbose: bool=True) -> bool:
        """Execute a command and return := 'response is OK'
        This routine can be used whenever we are simply interested in setting reader parameters,
        and do not expect any tag data to be returned."""
        resp_lst = self.execute_cmd(cmdstr)
        ret_code = BaseCommLink.return_code(resp_lst)
        is_ok = ret_code == BaseCommLink.RC_OK
        if not is_ok and verbose:
            print("Error code {} on cmd '{}'".format(ret_code, cmdstr))
            print("Err string: {}".format(BaseCommLink.RC_string(ret_code)))
        return is_ok

    def RadarSetup(self, EPCcode: str) -> None:
        """Set up the reader to search for a tag with a specific Electronic Product Code (EPC).
        by later on issuing RadarGet() commands.
        The 'Radar' functionality allows the user to search for a specific tag, and to determine
        its distance from the reader using the RSS (return signal strength) field.

        See the TLS document: 'Application\ Note\ -\ Advice\ for\ Implementing\ a\ Tag\ Finder\ Feature\ V1.0.pdf'
        """
        cmdstr = ".iv -x -n -ron -io off -qt b -qs s0 -sa 4 -st s0 -sb epc -sd {} -sl 30 -so 0020".format(EPCcode)
        if not self.execute_is_ok(cmdstr):
            raise RuntimeError("radarsetup failed")

    def RadarGet(self) -> RSSI:
        """Return an RSSI value of the tag previously selected by its EPC in RadarSetup"""
        resplst = self.execute_cmd(".iv")
        ret_code = BaseCommLink.return_code(resplst)
        if ret_code != BaseCommLink.RC_OK:
            raise RuntimeError("radarget failed")
        rssi_lst = BaseCommLink._extract_response(resplst, RI_VAL)
        if len(rssi_lst) != 1:
            raise RuntimeError("no single RSSI value detected: rssi_lst is {}".format(rssi_lst))
        return BaseCommLink._check_get_int_val(rssi_lst[0], RI_VAL)


class DummyCommLink(BaseCommLink):
    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.resplst: typing.List[str] = []

    def is_alive(self, doquick: bool=True) -> bool:
        return True

    def id_string(self) -> str:
        return "DummyCommLink {}".format(self.id)

    @staticmethod
    def get_cmd_from_str(cmdstr: str) -> typing.Tuple[str, dict]:
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
                    optval = None
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
        if cc == 'iv' and 'x' not in optdct:
            self.resplst.append('RI: -40')
        self.resplst.extend(['OK:', ''])

    def raw_read_response(self, timeout_secs: int) -> ResponseList:
        rlst = []
        done = len(self.resplst) == 0
        while not done:
            cur_line = self.resplst.pop(0).strip()
            if len(cur_line) > 0:
                rlst.append(BaseCommLink._line_2_resptup(cur_line))
            else:
                # we have reached a 'terminal' message (OK or ER)
                done = True
            done = len(self.resplst) == 0
        # --
        return rlst
