"""Implement some of the Technology Solutions (UK) TSL ASCII Protocoll 2.4
to control a RFID/bar code scanner over a serial device.

This module is based on the Technology Solutions documents available from
https://www.tsl.com/ .

All commands are of the form
'.'XY {'-'params}  <LF>
i.e. a period followed by a two letter command, then
a number of parameters beginning with '-', and
a linefeed.

Some parameters need to be enclosed in double quotes.
"""

import typing
from enum import Enum
import math

import gevent
import gevent.queue

import serverlib.commlink as commlink
import serverlib.Taskmeister as Taskmeister

from webclient.commonmsg import CommonMSG


BarcodeType = str

# and electronic producet code type. Also see is_valid_epc
EPCstring = str


class BuzzViblen(Enum):
    """Length of duration of buzzer sound or vibrator"""
    short = 'sho'
    medium = 'med'
    _long = 'lon'


class Buzzertone(Enum):
    """Pitch of buzzer tone"""
    low = 'low'
    med = 'med'
    high = 'hig'


ON_OFF_DCT = {True: 'on', False: 'off'}


class AlertParams:
    """Parameters that define an alert action."""
    def __init__(self,
                 buzzeron: bool, vibrateon: bool,
                 vblen: BuzzViblen, pitch: Buzzertone) -> None:
        """

        Args:
           buzzeron: switch the buzzer on/offs
           vibrateon: switch the RFID vibrator on/offs
           vblen: length of buzzer and vibrator if on respectively
           pitch: pitch of buzzer if on.
        """
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
        """

        Args:
           doalert: perform a predefined alert sequence upon reading?
           with_date_time: produce barcode data with timestamps of time read?
           read_time_secs: barcode read time out in seconds. This must be 1 <= X <= 9 .

        Raises:
           TypeError: if read_time_secs is not an int.
           ValueError: if read_time_secs is out of range.
        """
        self.doalert = doalert
        self.with_date_time = with_date_time
        self.read_time_secs = read_time_secs
        if not isinstance(read_time_secs, int):
            raise TypeError("integer expected")
        if read_time_secs < 1 or read_time_secs > 9:
            raise ValueError("BarcodeParams: read_time is out of range!")

    def tostr(self) -> str:
        """Convert these paramaters to a a string."""
        cmdstr = "-al {} -dt {} -t {}".format(ON_OFF_DCT[self.doalert],
                                              ON_OFF_DCT[self.with_date_time],
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
    """An RFID memory back selection type"""
    epc = 'epc'
    tid = 'tid'
    usr = 'usr'


class SelectTargetType(Enum):
    """An RFID back selection type"""
    s0 = 's0'
    s1 = 's1'
    s2 = 's2'
    s3 = 's3'
    sl = 'sl'


RFID_LST = [('do_alert', 'al'),
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

VALID_RFID_DCT = dict(RFID_LST)
# the order in this list is signicant: its the order in which the .iv parameters are interpreted
RFID_ORDER_LST = ['x', 'al', 'c', 'e', 'r', 'ie', 'dt', 'fs', 'ix', 'sb',
                  'so', 'sl', 'sd', 'o', 'io', 'sa', 'st', 'qa', 'ql', 'qs',
                  'qt', 'qv', 'fi', 'tf', 'p', 'n']

HEXNUMS = [chr(ord('0') + i) for i in range(10)]
HEXLETTERS = [chr(ord('A') + i) for i in range(6)]
HEXCHARS = frozenset(HEXNUMS + HEXLETTERS)


def is_hex_string(s: str) -> bool:
    """Return: 'this string contains only valid hex characters'"""
    return sum([ch in HEXCHARS for ch in s]) == len(s)


def is_valid_epc(epc: EPCstring) -> bool:
    """Perform a somple sanity check on the EPC code.
    Return 'the EPC code is not apparently broken'
    EPC code must be 96 bits in length. This is 24 4-bit hex characters.
    All characters must be hex characters
    """
    return isinstance(epc, EPCstring) and len(epc) == 24 and is_hex_string(epc)


class RFIDParams:
    """Parameters that define the readRFID command.
    See the .iv (inventory) command

    EPC: electronic product code
    RSSI: received signal strength indicator
    TID: transponder identifier

      * do_alert            -al  perform an alert after the inventory operation
      * with_epc_cs         -c   include the EPC checksum in the response
      * with_epc_pc         -e   include the EPC PC  (protocol control) in the response
      * with_fast_id        -fi  with Impinj fast ID (include TID in response)
      * strongest_RSSI_only -fs  only return the tag with the strongest return signal (RSSI)
      * with EPC            -ie  include the EPC in the response
      * with_RSSI           -r   include RSSI in the response
      * inventory_only      -io  inventory only (no select phase)
      * output_power        -o   output power in dBm  [10 .. 29]
      * use_fixed_Q         -qa  Use a dynamic or a fixed query window
      * qvalue              -qv  In the case of a fixed query window, the length of this
                             window [0..15]
      * query_select        -ql  query select type (SL, not SL, all)
      * query_session       -qs  [0..3]
      * query_target_a      -qt  query target A  (or B)
      * select_action       -sa  select action [0..7]
      * select_bank         -sb  bank to use for select mask
      * select_mask_data    -sd  select mask data
      * select_mask_len     -sl  length in bits of select mask
      * select_mask_shift   -so
      * select_target       -st
      * tag_focus_on        -tf  tag focus on
      * reset_to_default    -x   reset the parameters to defaults
    """
    def __init__(self, **kw) -> None:
        # self.doalert = doalert
        # self.with_date_time = with_date_time
        self.pdct: typing.Dict[str, str] = {}
        got_err = False
        for kuser, val in kw.items():
            kinternal = VALID_RFID_DCT.get(kuser, None)
            if kinternal is None:
                got_err = True
                print("unknown RFIDparam '{}'".format(kuser))
            else:
                self.pdct[kinternal] = val
        if got_err:
            raise RuntimeError("Error in RFIDParams")

    def tostr(self) -> str:
        """Convert these RFIDParams to a string."""
        retstr = ""
        for rfidopt in RFID_ORDER_LST:
            if rfidopt in self.pdct:
                optval = self.pdct.get(rfidopt, None)
                if optval is None:
                    retstr += "-{} ".format(rfidopt)
                else:
                    retstr += "-{} {}".format(rfidopt, optval)
        return retstr


class TlsMode(Enum):
    """TLS data mode"""
    stock = 'sto'
    radar = 'rad'
    undef = 'ude'


RItuple = typing.Tuple[str, int, float]

RIList = typing.List[RItuple]


RIdict = typing.Dict[str, int]

RIDList = typing.List[RIdict]


class RunningAve:
    """Implement a running average of distance values"""
    A_OFFSET = -65
    N_PROP_TEN = 2.7*10.0

    def __init__(self, logger, nave: int) -> None:
        self.logger = logger
        if nave <= 0:
            raise RuntimeError("Runningave: nave must be > 0")
        self.nave = nave
        self._dlst: RIDList = []

    def reset_average(self):
        """Reset the running average to start from scratch"""
        self._dlst = []

    @staticmethod
    def ri2dist(ri: int) -> float:
        """Use an approximate formula to convert an RI into a distance in metres.
        The formula for this is taken from here:
        https://electronics.stackexchange.com/questions/83354/calculate-distance-from-rssi
        The parameters for A_OFFSET were determined experimentally, and that for
        N_PROP_TEN was guessed. This is a value between 2.7 and 4.3 , with 2.0 for free space.
        """
        return math.pow(10.0, (ri - RunningAve.A_OFFSET)/-RunningAve.N_PROP_TEN)

    @staticmethod
    def _radar_data(logger, clresp: commlink.CLResponse) -> typing.Optional[RIdict]:
        """Extract epc, RI and distance in metres from a response from the
        RFID reader.
        This list can be empty if no RFID tags were in range.
        Return None if we cannot extract distance information.
        """
        ret_lst: typing.Optional[typing.Iterator[typing.Tuple[str, int]]] = None
        ret_code: commlink.TLSRetCode = clresp.return_code()
        if ret_code in (commlink.BaseCommLink.RC_NO_TAGS,
                        commlink.BaseCommLink.RC_NO_BARCODE):
            # the scan event failed to return any EPC or barcode data
            # -> we return an empty list
            ret_lst = iter([])
        else:
            eplst = clresp[commlink.EP_VAL]
            rrlst = clresp[commlink.RI_VAL]
            if eplst is None or rrlst is None:
                return None
            rilst: typing.Optional[typing.List[int]] = None
            try:
                rilst = [int(sri) for sri in rrlst]
            except (ValueError, TypeError) as err:
                logger.error("radar mode: failed to retrieve RI values {}".format(err))
            ret_lst = zip(eplst, rilst) if rilst is not None and len(eplst) == len(rilst) else None
        return None if ret_lst is None else dict(ret_lst)

    @staticmethod
    def do_ave(tlst: typing.List[int]) -> int:
        """Average the RI values in the list.
        tlst: the list of values to average over.

        If a return did not happen in a particular instance, then we currently ignore
        that now, i.e. just return the normal, average using the actual number of
        elements in the list....
        """
        return sum(tlst)//len(tlst)

    def add_clresp(self, clresp: commlink.CLResponse) -> None:
        """Add the radar data from a commlink response to the curren running average."""
        ridct = RunningAve._radar_data(self.logger, clresp)
        if ridct is not None:
            self._dlst.append(ridct)
        while len(self._dlst) > self.nave:
            self._dlst.pop(0)

    def get_runningave(self) -> typing.Optional[RIList]:
        """Return a running average of distances using the cached data.
        Return None if we do not have sufficient data for a running average.
        """
        if len(self._dlst) < self.nave:
            return None
        sumdct: typing.Dict[str, typing.List[int]] = {}
        for vdct in self._dlst:
            for epc, ri_val in vdct.items():
                assert isinstance(ri_val, int), "INT expected {}".format(ri_val)
                sumdct.setdefault(epc, []).append(ri_val)
        do_ave = RunningAve.do_ave
        calc_dst = RunningAve.ri2dist
        ret_lst = [(epc, ri_ave, calc_dst(ri_ave)) for epc, ri_ave in
                   [(epc, do_ave(vlst)) for epc, vlst in sumdct.items() if len(vlst) > 0]]
        ret_lst.sort(key=lambda a: a[0])
        return ret_lst


class TLSReader(Taskmeister.BaseTaskMeister):
    """Create a class that can talk to the RFID reader via the provided commlink class.
       This class will convert data received from the RFID reader into CommonMSG instances
       and put them on the provided message queue.
    """
    def __init__(self, msg_q: gevent.queue.Queue,
                 logger,
                 cl: commlink.BaseCommLink,
                 radar_ave_num: int) -> None:
        super().__init__(msg_q, logger, 0.0, True)
        self._lverb = False
        self._cl = cl
        self.mode = TlsMode.undef
        print("TLS init")
        self.cur_state: typing.Optional[int] = None
        print("TLS init got {}".format(self.cur_state))
        if cl.is_alive():
            self.bt_set_stock_check_mode()
        self.runningave = RunningAve(logger, radar_ave_num)

    def _sendcmd(self, cmdstr: str, comment: str = None) -> None:
        cl = self._cl
        if cl.is_alive():
            cl.send_cmd(cmdstr, comment)
        else:
            self._log_error('commlink is not alive')

    def is_in_radarmode(self) -> bool:
        """Is the reader in radar mode ?"""
        return self.mode == TlsMode.radar

    def _convert_message(self, clresp: commlink.CLResponse) -> typing.Optional[CommonMSG]:
        """Convert an RFID response into a common message.
        Return None if this message should not be passed on.
        """
        # assume that we are going to return this message...
        ret_code: commlink.TLSRetCode = clresp.return_code()
        if ret_code == commlink.BaseCommLink.RC_TIMEOUT:
            return CommonMSG(CommonMSG.MSG_SV_RFID_STATREP, CommonMSG.RFID_TIMEOUT)
        ret_is_ok = (ret_code == commlink.BaseCommLink.RC_OK)
        # A: determine the kind of message to return based on the comment_dict
        # or the current mode
        # Our decision is stored into msg_type
        msg_type = None
        ret_data: typing.Optional[typing.List[typing.Any]] = None
        comm_dct = clresp.get_comment_dct()
        if comm_dct is None:
            comment_str = None
        else:
            comment_str = comm_dct.get(commlink.BaseCommLink.COMMENT_ID, None)
            self._log_debug("clresp comment {}, Comment: {}".format(clresp, comment_str))
        if comment_str is None:
            # we have a message because the user pressed the trigger --
            # try to determine what kind of message to send back
            # based on our current mode
            if self.mode == TlsMode.radar:
                msg_type = CommonMSG.MSG_RF_RADAR_DATA
            elif self.mode == TlsMode.stock:
                msg_type = CommonMSG.MSG_RF_CMD_RESP
            else:
                self._log_debug('no comment_str and no mode: returning None')
                msg_type = None
        elif comment_str == 'radarsetup':
            # the server has previously sent a command to the RFID reader to go into
            # radar mode. We generate a message only if this failed.
            if not ret_is_ok:
                msg_type = CommonMSG.MSG_RF_CMD_RESP
        elif comment_str == 'RAD':
            msg_type = CommonMSG.MSG_RF_RADAR_DATA
        elif comment_str == 'IVreset':
            if not ret_is_ok:
                msg_type = CommonMSG.MSG_RF_CMD_RESP
        else:
            self._log_error('unhandled comment string {}'.format(comment_str))
        # B: now try to determine ret_data.
        if msg_type is None:
            return None
        if msg_type == CommonMSG.MSG_RF_RADAR_DATA:
            self.runningave.add_clresp(clresp)
            ret_data = self.runningave.get_runningave()
            self._log_debug("Returning radar data {}".format(ret_data))
        elif msg_type == CommonMSG.MSG_RF_CMD_RESP:
            ret_data = clresp.rl
        # do something with ret_data here and return a CommonMSG or None
        if ret_data is None:
            return None
        assert msg_type is not None and ret_data is not None, "convert_message error 99"
        return CommonMSG(msg_type, ret_data)

    # stocky main server messaging service....
    def generate_msg(self) -> typing.Optional[CommonMSG]:
        """Read a message from the RFID reader device if one is present.
        Convert this message into a CommonMsg instance or None and return it.
        The returned message will be put on the TaskMeister's queue.

        Typically, when the user presses the trigger of the RFID reader,
        we will send a message with the scanned data back.

        Note:
           This method overrules the method defined in BaseTaskMeister.
        """
        self._log_debug("TLS GM enter")
        # check for a change of the state of the commlink first.
        # if the state has changed, report this.
        new_state = self._cl.get_rfid_state()
        if new_state != self.cur_state:
            self.cur_state = new_state
            self._log_debug("TLS: state change reported. new state: {}".format(new_state))
            return CommonMSG(CommonMSG.MSG_SV_RFID_STATREP, new_state)
        # no state change. if its up:
        #   read something (blocking) and return that (could be None)
        # else:
        #   return None the taskmeister will ignore it.
        if self.cur_state == CommonMSG.RFID_ON:
            self._log_debug("TLS before read... ")
            clresp: commlink.CLResponse = self._cl.raw_read_response()
            self._log_debug("TLS got {}".format(clresp))
            return self._convert_message(clresp)
        self._log_debug("TLS state is: {}, returning None".format(self.cur_state))
        return None

    def set_region(self, region_code: str) -> None:
        """Set the geographic region of the RFID reader.

        Args:
           region_code: The region code to set. Examples of this are 'us', 'eu', 'tw', etc.

        Raises:
           TypeError: if region_code is not a string.
           ValueError: if the length of region_code is not 2.
        Note:
           Not all 1128 readers support this command and will return an error message
           instead.
        """
        if not isinstance(region_code, str):
            raise TypeError('string expected for region code')
        if len(region_code) != 2:
            raise ValueError("length of region code <> 2!")
        cmdstr = ".sr -s {}".format(region_code)
        self._sendcmd(cmdstr)

    def doalert(self, p: AlertParams) -> None:
        """Perform the alert command: play a tone and/or buzz the vibrator
        in the reader.

        Args:
           p: defines the actions for the reader to perform.
        """

        cmdstr = ".al -b{} -v{} -d{} -t{}\n".format(ON_OFF_DCT[p.buzzeron],
                                                    ON_OFF_DCT[p.vibrateon],
                                                    p.vblen.value,
                                                    p.pitch.value)
        self._sendcmd(cmdstr)

    def set_alert_default(self, p: AlertParams) -> None:
        """Set the default alert parameters."""
        cmdstr = ".al -b{} -v{} -d{} -t{} -n\n".format(ON_OFF_DCT[p.buzzeron],
                                                       ON_OFF_DCT[p.vibrateon],
                                                       p.vblen.value,
                                                       p.pitch.value)
        self._sendcmd(cmdstr)

    def send_abort(self) -> None:
        """Abort the current command."""
        cmdstr = ".ab\n"
        self._sendcmd(cmdstr)

    def set_readbarcode_params(self, p: BarcodeParams) -> None:
        """Read the curren bar code parameters from the RFID reader."""
        cmdstr = ".bc " + p.tostr() + " -n\n"
        self._sendcmd(cmdstr, "bcparams")

    def readbarcode(self, p: BarcodeParams) -> None:
        """Perform a read barcode operation. If p is None, use the
        default parameters currently in effect.
        """
        cmdstr = ".bc "
        if p is not None:
            cmdstr += p.tostr()
        cmdstr += " -n\n"
        self._sendcmd(cmdstr, "bcdata")

    def set_bluetooth(self,
                      bt_on: bool,
                      bundle_id: str,
                      bundle_seed_id: str,
                      bt_name: str,
                      bt_spp: bool,
                      bt_pairing_code: str) -> None:
        """Set the bluetooth parameters.

        Args:
           bt_on: switch the bluetooth transmitter on/official
           bundle_id: a string
           bundle_seed_id: a string
           bt_name: the name the RFID read will identify as in Bluetooth mode.
           bt_spp: use bluetooth SPP mode
           bt_pairing_code: the code which will be required for a device to
           pair with the RFID reader over bluetooth.
        Note:
           This command is only available over a USB connection and always
           performs a reset of the reader.

        Raises:
           TypeError: if any argument has an unexpected type.
           ValueError: if len(bt_pairing_code) != 4.
        """
        if sum([isinstance(var, tt) for var, tt in [(bt_on, bool), (bundle_id, str),
                                                    (bundle_seed_id, str),
                                                    (bt_name, str),
                                                    (bt_spp, bool),
                                                    (bt_pairing_code, str)]]) != 6:
            raise TypeError('illegal types for set_bluetooth')
        if len(bt_pairing_code) != 4:
            raise ValueError("BT pairing code <> length 4!")
        protoname = 'spp' if bt_spp else 'hid'
        cmdstr = '.bt -e{} -f"{}" -w{} -bi"{}" -bs"{}" -m{}\n'.format(ON_OFF_DCT[bt_on],
                                                                      bt_name,
                                                                      bt_pairing_code,
                                                                      bundle_id, bundle_seed_id,
                                                                      protoname)
        self._sendcmd(cmdstr, "setbt")

    def set_date_time(self, yy: int, mm: int, dd: int,
                      hrs: int, mins: int, secs: int) -> None:
        """Set the date and time of the RFID reader.

        Args:
           yy: the year >= 2000.
           mm: the month 1 <= x <= 12
           dd: the day of the month
           hrs: the hour of the day in  24 hour format.
           mins: the minutes of the hour
           secs: the second of the minute.

        Raises:
           TypeError: if any argument is not an integer
           ValueError: if any argument is out of range.

        Note:
          This routine does *NOT* check whether, collectively,
          the arguments constitute a valid calendar date. E.g. setting
          a date of 30th February will be silently allowed.
        """
        if isinstance(hrs, int):
            if not 0 <= hrs <= 24:
                raise ValueError("hour is out of range")
        else:
            raise TypeError('int expected for hrs')
        if isinstance(mins, int):
            if not 0 <= mins < 60:
                raise ValueError("minute is out of range")
        else:
            raise TypeError('int expected for mins')
        if isinstance(secs, int):
            if not 0 <= secs < 60:
                raise ValueError("second is out of range")
        else:
            raise TypeError('int expected for secs')
        cmdstr = ".tm -s {:02d}{:02d}{:02d}".format(hrs, mins, secs)
        self._sendcmd(cmdstr, "settime")

        if isinstance(yy, int):
            if yy < 2000:
                raise ValueError("year is out of range")
        else:
            raise TypeError('int expected for year')
        if isinstance(mm, int):
            if not 1 <= mm <= 12:
                raise ValueError("month is out of range")
        else:
            raise TypeError('int expected for month')
        if isinstance(dd, int):
            if not 1 <= dd <= 31:
                raise ValueError("day is out of range")
        else:
            raise TypeError('int expected for day')
        cmdstr = ".da -s {:02d}{:02d}{:02d}".format(yy-2000, mm, dd)
        self._sendcmd(cmdstr, "setdate")

    def reset_inventory_options(self):
        """Issue a command to reset the .iv options to the default ones."""
        self._sendcmd(".iv -x", "IVreset")

    def bt_set_radar_mode(self, epc: typing.Optional[EPCstring]) -> None:
        """Set up the reader to search for a tag with a
           specific Electronic Product Code (EPC) by later on issuing RadarGet() commands.

        Args:
           epc: the EPC of the RFID tag to track. None means all tags will be tracked.

        The 'Radar' functionality allows the user to search for a specific tag, and
        to determine its distance from the reader using the RSS (return signal strength) field.
        Note:
           See the TLS document: 'Application Note - Advice for Implementing a Tag Finder Feature V1.0.pdf'
        """
        if epc is not None:
            if not is_valid_epc(epc):
                raise ValueError("radarsetup: illegal EPC: '{}'".format(epc))
        # NOTE: epc currently not actually used....
        self.mode = TlsMode.radar
        self.reset_inventory_options()
        cmdstr = ".iv -al off -x -n -fi on -ron -io off -qt b -qs s0 -sa 4 -st s0 -sl 30 -so 0020"
        self._sendcmd(cmdstr, "radarsetup")

    def radar_get(self) -> None:
        """Issue a command to get the RSSI value of the tag previously selected
        by its EPC in RadarSetup.
        The response will be available on the response queue."""
        self._sendcmd(".iv", comment='RAD')

    def bt_set_stock_check_mode(self):
        """Set the RFID reader into stock taking mode."""
        self.mode = TlsMode.stock
        self.reset_inventory_options()
        alert_parms = AlertParams(buzzeron=False, vibrateon=True,
                                  vblen=BuzzViblen('med'),
                                  pitch=Buzzertone('med'))
        self.doalert(alert_parms)

    def send_rfid_msg(self, msg: CommonMSG) -> None:
        """The stocky server uses this routine to send messages (commands) to the
        RFID reader device.

        Args:
           msg: the message to translate into commands to the RFID reader.

        Raises:
           TypeError: if msg is not a CommonMSG instance.
           RuntimeError: if the command is of a type not implemented.
        """
        if not isinstance(msg, CommonMSG):
            raise TypeError('CommonMSG instance expected')
        if msg.msg == CommonMSG.MSG_WC_RADAR_MODE:
            want_radar_on = msg.data
            is_radar_on = self.is_in_radarmode()
            if want_radar_on != is_radar_on:
                if want_radar_on:
                    self.bt_set_radar_mode(epc=None)
                else:
                    self.bt_set_stock_check_mode()
        elif msg.msg == CommonMSG.MSG_SV_GENERIC_COMMAND:
            self.mode = TlsMode.stock
            # self.BT_set_stock_check_mode()
            cmdstr = msg.data
            # print("BLACMD {}".format(cmdstr))
            self._sendcmd(cmdstr, "radarsetup")
        else:
            self._log_warning("TLS skipping msg {}".format(msg))
            raise RuntimeError("do not know how to handle message")

    def write_user_bank(self, epc: EPCstring, data: str) -> None:
        """Select a tag with the provided EPC code and write
        the data string to the user bank.

        Args:
           epc: the EPC of the RFID tag to write to.
           data: the data string to write to the RFID tag's user bank.
                 This is a string containing ASCII-hex characters
                 which must be a multiple of four (only words can be written).

        Note:
           This command string was adapted from the document provided
           by TSL to their customers:
           Application Note - Selecting Reading and Writing Transponders
           with the TSL ASCII 2 Protocol V1.33.pdf

        Raises:
           ValueError: if is_valid_epc(epc) returns False or len(data) is not
              a multiple of 4.
           TypeError: if data is not an instance of string.
        """
        if not is_valid_epc(epc):
            raise ValueError("illegal EPC = '{}'".format(epc))
        if isinstance(data, str):
            if not (len(data) % 4 == 0 and is_hex_string(data)):
                raise ValueError("invalid data string '{}".format(data))
        else:
            raise TypeError('data string expected')
        d_len = len(data) // 4
        # this determined the location in the user bank to write the data
        data_offset = '0005'
        cmdstr = """.wr -db usr -da {} -dl {} -do {} -ql all -qs s1 -qt b -sa 4 -sb epc
 -sd {} -sl 60 -so 0020 -st s1""".format(data, d_len, data_offset, epc)
        self._sendcmd(cmdstr, comment='WRITE')

    def read_user_bank(self, epc: EPCstring, num_chars: int) -> None:
        """Select a tag with the provided EPC code and read out the
        data string from the tag's user bank.

        Args:
           epc: the EPC of the RFID tag to read from
           num_chars: the number of bytes (chars) to read from the user bank.

        Raises:
           ValueError: if is_valid_epc(epc) returns False or num_chars is not a multiple
           of four.
           TypeError: if num_chars is not an integer.
        """
        if not is_valid_epc(epc):
            raise ValueError("illegal EPC = '{}'".format(epc))
        if isinstance(num_chars, int):
            if num_chars % 4 != 0:
                raise ValueError("invalid num_chars '{}'".format(num_chars))
        else:
            raise TypeError('num_chars: int expected')
        d_len = num_chars // 4
        data_offset = '0005'
        cmdstr = """.rd -db usr -dl {} -do {} -ql all -qs s1 -qt b -sa 4 -sb epc -sd {}
 -sl 60 -so 0020 -st s1""".format(d_len, data_offset, epc)
        self._sendcmd(cmdstr, comment='READ')
