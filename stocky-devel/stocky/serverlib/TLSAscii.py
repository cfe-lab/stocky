
import typing
from enum import Enum

import gevent.queue

import serverlib.commlink as commlink
import serverlib.Taskmeister as Taskmeister

from webclient.commonmsg import CommonMSG

"""Implement some of the Technology Solutions (UK) TSL ASCII Protocoll 2.4
to control a RFID/bar code scanner over a serial device.

This module is based on the Technology Solutions document available from www.tsl.com.

All commands are of the form
'.'XY {'-'params}  <LF>

i.e. a period followed by a two letter command, then
a number of paramater beginning with '-', and
a linefeed.

Some parameters need to enclosed in double quotes.

"""

BarcodeType = str


class BuzzViblen(Enum):
    """length of buzzer or vibrator"""
    short = 'sho'
    medium = 'med'
    _long = 'lon'


class Buzzertone(Enum):
    low = 'low'
    med = 'med'
    high = 'hig'


onoffdct = {True: 'on', False: 'off'}


class AlertParams:
    """Parameters that define an alert action."""
    def __init__(self,
                 buzzeron: bool, vibrateon: bool,
                 vblen: BuzzViblen, pitch: Buzzertone) -> None:
        self.buzzeron = buzzeron
        self.vibrateon = vibrateon
        self.vblen = vblen
        self.pitch = pitch


class BarcodeParams:
    """Parameters that define a readBarcode command."""
    def __init__(self,
                 doalert: bool,
                 with_date_time: bool,
                 read_time_secs: int) -> None:
        self.doalert = doalert
        self.with_date_time = with_date_time
        self.read_time_secs = read_time_secs
        if read_time_secs < 1 or read_time_secs > 9:
            raise RuntimeError("BarcodeParams: read_time is out of range!")

    def tostr(self) -> str:
        cmdstr = "-al {} -dt {} -t {}".format(onoffdct[self.doalert],
                                              onoffdct[self.with_date_time],
                                              self.read_time_secs)
        return cmdstr


class QStype(Enum):
    """An inventory query select state.
    Select transponders based on their SL bit.
    """
    _all = 'all'
    nsl = 'nsl'
    sl = 'sl'


class BankSelectType(Enum):
    epc = 'epc'
    tid = 'tid'
    usr = 'usr'


class SelectTargetType(Enum):
    s0 = 's0'
    s1 = 's1'
    s2 = 's2'
    s3 = 's3'
    sl = 'sl'


rfid_lst = [('do_alert', 'al'),
            ('with_epc_cs', 'c'),
            ('with_epc_pc', 'e'),
            ('with_fast_id', 'fi'),
            ('strongest_RSSI_only', 'fs'),
            ('with_EPC', 'ie'),
            ('inventory_only', 'io'),
            ('index_response', 'ix'),
            ('no_action', 'n'),
            ('output_power', 'o'),
            ('list_params', 'n'),
            ('use_fixed_Q', 'qa'),
            ('qvalue', 'qv'),
            ('query_select', 'ql'),
            ('query_session', 'qs'),
            ('query_target_a', 'qt'),
            ('qvalue', 'qv'),
            ('with_RSSI', 'r'),
            ('select_action', 'sa'),
            ('select_bank', 'sb'),
            ('select_mask_data', 'sd'),
            ('select_mask_len', 'sl'),
            ('select_mask_shift', 'so'),
            ('select_target', 'st'),
            ('tag_focus_on', 'tf'),
            ('reset_to_default', 'x')]

valid_rfid_dct = dict(rfid_lst)
# the order in this list is signicant: its the order in which the .iv parameters are interpreted
rfid_order_lst = ['x', 'al', 'c', 'e', 'r', 'ie', 'dt', 'fs', 'ix', 'sb',
                  'so', 'sl', 'sd', 'o', 'io', 'sa', 'st', 'qa', 'ql', 'qs',
                  'qt', 'qv', 'fi', 'tf', 'p', 'n']


class RFIDParams:
    """Parameters that define the readRFID command.
    See the .iv (inventory) command

    EPC: electronic product code
    RSSI: received signal strength indicator
    TID: transponder identifier

    do_alert            -al  perform an alert after the inventory operation
    with_epc_cs         -c   include the EPC checksum in the response
    with_epc_pc         -e   include the EPC PC  (protocol control) in the response
    with_fast_id        -fi  with Impinj fast ID (include TID in response)
    strongest_RSSI_only -fs  only return the tag with the strongest return signal (RSSI)
    with EPC            -ie  include the EPC in the response
    with_RSSI           -r   include RSSI in the response
    inventory_only      -io  inventory only (no select phase)
    output_power        -o   output power in dBm  [10 .. 29]
    use_fixed_Q         -qa  Use a dynamic or a fixed query window
    qvalue              -qv  In the case of a fixed query window, the length of this
                             window [0..15]
    query_select        -ql  query select type (SL, not SL, all)
    query_session       -qs  [0..3]
    query_target_a      -qt  query target A  (or B)

    select_action       -sa  select action [0..7]
    select_bank         -sb  bank to use for select mask
    select_mask_data    -sd  select mask data
    select_mask_len     -sl  length in bits of select mask
    select_mask_shift   -so
    select_target       -st
    tag_focus_on        -tf  tag focus on
    reset_to_default    -x   reset the parameters to defaults
    """
    def __init__(self, **kw) -> None:
        # self.doalert = doalert
        # self.with_date_time = with_date_time
        self.pdct: typing.Dict[str, str] = {}
        got_err = False
        for kuser, v in kw.items():
            kinternal = valid_rfid_dct.get(kuser, None)
            if kinternal is None:
                got_err = True
                print("unknown RFIDparam '{}'".format(kuser))
            else:
                self.pdct[kinternal] = v
        if got_err:
            raise RuntimeError("Error in RFIDParams")

    def tostr(self) -> str:
        retstr = ""
        for rfidopt in rfid_order_lst:
            if rfidopt in self.pdct:
                optval = self.pdct.get(rfidopt, None)
                if optval is None:
                    retstr += "-{} ".format(rfidopt)
                else:
                    retstr += "-{} {}".format(rfidopt, optval)
        return retstr


class TLSReader(Taskmeister.BaseTaskMeister):
    def __init__(self, msgQ: gevent.queue.Queue, logger, cl: commlink.BaseCommLink) -> None:
        """Create a class that can talk to the RFID reader via the provided commlink class."""
        super().__init__(msgQ, logger)
        self._cl = cl

    def _sendcmd(self, cmdstr: str) -> commlink.ResponseList:
        cl = self._cl
        if not cl.is_alive():
            raise RuntimeError("commlink is not alive")
        return cl.execute_cmd(cmdstr)

    def _send_command_check_ok(self, cmdstr: str) -> None:
        """Send a command to the RFID reader and check that the response
        is OK.
        Raise an exception if it is not.
        """
        cl = self._cl
        if not cl.is_alive():
            msg = "TLS: commlink is not alive"
            self.logger.error(msg)
            raise RuntimeError(msg)
        if not cl.execute_is_ok(cmdstr, verbose=True):
            msg = "TLS: _send_command_check_ok failed for '{}'".format(cmdstr)
            self.logger.error(msg)
            raise RuntimeError(msg)

    def set_region(self, region_code: str) -> None:
        """Set the geographic region of the RFID reader.
        Examples of this are 'us', 'eu', 'tw', etc.
        NOTE: not all 1128 readers support this command and will return and error message
        instead.
        """
        if len(region_code) != 2:
            raise RuntimeError("length of region code <> 2!")
        cmdstr = ".sr -s {}".format(region_code)
        # the operation might not be supported by the reader.. gracefully handle this case
        # self._send_command_check_ok(cmdstr)
        if not self._cl.execute_is_ok(cmdstr, verbose=True):
            msg = "TLS: command failed for '{}'".format(cmdstr)
            self.logger.error(msg)

    def doalert(self, p: AlertParams) -> None:
        """Perform the alert command: play a tone and/or buzz the vibrator
        in the reader."""

        cmdstr = ".al -b{} -v{} -d{} -t{}\n".format(onoffdct[p.buzzeron],
                                                    onoffdct[p.vibrateon],
                                                    p.vblen.value,
                                                    p.pitch.value)
        self._sendcmd(cmdstr)

    def set_alert_default(self, p: AlertParams) -> None:
        """Set the default alert parameters."""
        pass

    def get_alert_default(self) -> AlertParams:
        """Return the current default alert parameters."""

    def abort(self) -> None:
        """Abort the current command."""
        cmdstr = ".ab\n"
        self._sendcmd(cmdstr)

    def set_readbarcode_params(self, p: BarcodeParams) -> None:
        cmdstr = ".bc " + p.tostr() + " -n\n"
        self._sendcmd(cmdstr)

    def get_readbarcode_params(self) -> BarcodeParams:
        pass

    def readbarcode(self, p: BarcodeParams) -> BarcodeType:
        """Perform a read barcode operation. If p is None, use the
        default parameters currently in effect.
        """
        cmdstr = ".bc "
        if p is not None:
            cmdstr += p.tostr()
        cmdstr += " -n\n"
        self._sendcmd(cmdstr)

    def set_bluetooth(self,
                      bt_on: bool,
                      bundle_id: str,
                      bundle_seed_id: str,
                      bt_name: str,
                      bt_spp: bool,
                      bt_pairing_code: str) -> None:
        """Set the bluetooth parameters. This command is only available over
        a USB connection and always performs a reset of the reader.
        """
        if len(bt_pairing_code) != 4:
            raise RuntimeError("BT pairing code <> length 4!")
        protoname = 'spp' if bt_spp else 'hid'
        cmdstr = '.bt -e{} -f"{}" -w{} -bi"{}" -bs"{}" -m{}\n'.format(onoffdct[bt_on],
                                                                      bt_name,
                                                                      bt_pairing_code,
                                                                      bundle_id, bundle_seed_id,
                                                                      protoname)
        self._send_command_check_ok(cmdstr)

    def set_date_time(self, yy: int, mm: int, dd: int,
                      hrs: int, mins: int, secs: int) -> None:
        """Set the date and time of reader.

        The hour (hh parameter) is in  24 hour format.
        """
        if not (0 <= hrs <= 24):
            raise RuntimeError("hour is out of range")
        if not (0 <= mins < 60):
            raise RuntimeError("minute is out of range")
        if not (0 <= secs < 60):
            raise RuntimeError("second is out of range")
        cmdstr = ".tm -s {:02d}{:02d}{:02d}".format(hrs, mins, secs)
        self._send_command_check_ok(cmdstr)

        if yy < 2000:
            raise RuntimeError("year is out of range")
        if not (1 <= mm <= 12):
            raise RuntimeError("month is out of range")
        if not (1 <= dd <= 31):
            raise RuntimeError("day is out of range")
        cmdstr = ".da -s {:02d}{:02d}{:02d}".format(yy-2000, mm, dd)
        self._send_command_check_ok(cmdstr)

    def readRFID(self, p: RFIDParams) -> None:
        pass

    def RadarSetup(self, EPCcode: str) -> None:
        """Set up the reader to search for a tag with a specific Electronic Product Code (EPC).
        by later on issuing RadarGet() commands.
        The 'Radar' functionality allows the user to search for a specific tag, and to determine
        its distance from the reader using the RSS (return signal strength) field.

        See the TLS document: 'Application\ Note\ -\ Advice\ for\ Implementing\ a\ Tag\ Finder\ Feature\ V1.0.pdf'
        """
        cmdstr = ".iv -x -n -ron -io off -qt b -qs s0 -sa 4 -st s0 -sb epc -sd {} -sl 30 -so 0020".format(EPCcode)
        if not self._cl.execute_is_ok(cmdstr):
            raise RuntimeError("radarsetup failed")

    def RadarGet(self) -> commlink.RSSI:
        """Return an RSSI value of the tag previously selected by its EPC in RadarSetup"""
        resplst = self._cl.execute_cmd(".iv")
        ret_code = commlink.BaseCommLink.return_code(resplst)
        if ret_code != commlink.BaseCommLink.RC_OK:
            raise RuntimeError("radarget failed")
        rssi_lst = commlink.BaseCommLink._extract_response(resplst, commlink.RI_VAL)
        if len(rssi_lst) != 1:
            raise RuntimeError("no single RSSI value detected: rssi_lst is {}".format(rssi_lst))
        return commlink.BaseCommLink._check_get_int_val(rssi_lst[0], commlink.RI_VAL)

    def BT_set_stock_check_mode(self):
        """Set the RFID reader into stock taking mode."""
        alert_parms = AlertParams(buzzeron=False, vibrateon=True,
                                  vblen=BuzzViblen('med'),
                                  pitch=Buzzertone('med'))
        self.doalert(alert_parms)

    # stocky main server messaging service....
    def generate_msg(self) -> CommonMSG:
        """Block and return a message to the web server
        Typically, when the user presses the trigger of the RFID reader,
        we will send a message with the scanned data back.
        NOTE: this method is overrulling the BaseTaskMeister method
        """
        time_out_secs = 10
        resp_lst = self._cl.raw_read_response(time_out_secs)
        self.logger.debug("YEEEEE got {}".format(resp_lst))
        # do something with resp_lst here and return a CommonMSG
        return None

    def send_RFID_msg(self, msg: CommonMSG) -> None:
        """The stocky server uses this routine to send messages (commands) to the
        RFID reader device."""
        if msg.msg == CommonMSG.MSG_WC_STOCK_CHECK:
            self.BT_set_stock_check_mode()
