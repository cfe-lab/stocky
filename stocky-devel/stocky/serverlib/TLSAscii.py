
import typing
from enum import Enum
import math

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


class tls_mode(Enum):
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
    def __init__(self, logger, Nave: int) -> None:
        self.logger = logger
        if Nave <= 0:
            raise RuntimeError("Runningave: Nave must be > 0")
        self.Nave = Nave
        self._dlst: RIDList = []

    def reset_average(self):
        self._dlst = []

    @staticmethod
    def RI2dist(ri: int) -> float:
        """Use an approximate formula to convert an RI into a distance in metres.
        The formula for this is taken from here:
        https://electronics.stackexchange.com/questions/83354/calculate-distance-from-rssi
        The parameters for A_OFFSET were determined experimentally, and that for
        N_PROP_TEN was guessed. This is a value between 2.7 and 4.3 , with 2.0 for free space.
        """
        A_OFFSET = -65
        N_PROP_TEN = 2.7*10.0
        return math.pow(10.0, (ri - A_OFFSET)/-N_PROP_TEN)

    @staticmethod
    def _radar_data(logger, clresp: commlink.CLResponse) -> typing.Optional[RIdict]:
        """Extract epc, RI and distance in metres from a response from the
        RFID reader.
        This list can be empty if no RFID tags were in range.
        Return None if we cannot extract distance information.
        """
        ret_lst: typing.Optional[typing.Iterator[typing.Tuple[str, int]]] = None
        ret_code: commlink.TLSRetCode = clresp.return_code()
        if ret_code == commlink.BaseCommLink.RC_NO_TAGS or\
           ret_code == commlink.BaseCommLink.RC_NO_BARCODE:
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
            except (ValueError, TypeError) as e:
                logger.error("radar mode: failed to retrieve RI values {}".format(e))
            ret_lst = zip(eplst, rilst) if rilst is not None and len(eplst) == len(rilst) else None
        return None if ret_lst is None else dict(ret_lst)

    @staticmethod
    def do_ave(numexp: int, tlst: typing.List[int]) -> int:
        """Average the RI values in the list.
        numexp: is the number of times the RFID tags were queried.

        If a return did not happen in a particular instance, then we currently ignore
        that now, i.e. just return the normal, average using the actual number of
        elements in the list....
        """
        return sum(tlst)//len(tlst)

    def add_clresp(self, clresp: commlink.CLResponse) -> None:
        ridct = RunningAve._radar_data(self.logger, clresp)
        if ridct is not None:
            self._dlst.append(ridct)
        while len(self._dlst) > self.Nave:
            self._dlst.pop(0)

    def get_runningave(self) -> typing.Optional[RIList]:
        """Return a running average of distances using the cached data.
        Return None if we do not have sufficient data for a running average.
        """
        if len(self._dlst) < self.Nave:
            return None
        sumdct: typing.Dict[str, typing.List[int]] = {}
        for vdct in self._dlst:
            for epc, ri in vdct.items():
                assert isinstance(ri, int), "INT expected {}".format(ri)
                sumdct.setdefault(epc, []).append(ri)
        do_ave = RunningAve.do_ave
        calc_dst = RunningAve.RI2dist
        ret_lst = [(epc, ri_ave, calc_dst(ri_ave)) for epc, ri_ave in
                   [(epc, do_ave(self.Nave, vlst)) for epc, vlst in sumdct.items() if len(vlst) > 0]]
        ret_lst.sort(key=lambda a: a[0])
        return ret_lst


class TLSReader(Taskmeister.BaseReader):
    def __init__(self, msgQ: gevent.queue.Queue,
                 logger,
                 cl: commlink.BaseCommLink,
                 radar_ave_num: int) -> None:
        """Create a class that can talk to the RFID reader via the provided commlink class."""
        super().__init__(msgQ, logger)
        self._cl = cl
        self.mode = tls_mode(tls_mode.undef)
        self.runningave = RunningAve(logger, radar_ave_num)

    def _sendcmd(self, cmdstr: str, comment: str=None) -> None:
        cl = self._cl
        if not cl.is_alive():
            raise RuntimeError("commlink is not alive")
        cl.send_cmd(cmdstr, comment)

    def is_in_radarmode(self) -> bool:
        return self.mode == tls_mode.radar

    def _convert_message(self, clresp: commlink.CLResponse) -> typing.Optional[CommonMSG]:
        """Convert a RFID response into a common message.
        Return None if this message should not be passed on.
        """
        # assume that we are going to return this message...
        ret_code: commlink.TLSRetCode = clresp.return_code()
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
            self.logger.debug("clresp comment {}, Comment: {}".format(clresp, comment_str))
        if comment_str is None:
            # we have a message because the user pressed the trigger --
            # try to determine what kind of message to send back
            # based on our current mode
            if self.mode == tls_mode.radar:
                msg_type = CommonMSG.MSG_RF_RADAR_DATA
            elif self.mode == tls_mode.stock:
                msg_type = CommonMSG.MSG_RF_STOCK_DATA
            elif self.mode == tls_mode.undef:
                msg_type = CommonMSG.MSG_RF_CMD_RESP
            else:
                raise RuntimeError('unknown mode')
        elif comment_str == 'radarsetup':
            if not ret_is_ok:
                msg_type = CommonMSG.MSG_RF_CMD_RESP
        elif comment_str == 'RAD':
            msg_type = CommonMSG.MSG_RF_RADAR_DATA
        elif comment_str == 'IVreset':
            return None
        else:
            self.logger.error('unhandled comment string {}'.format(comment_str))
        # B: now try to determine ret_data.
        if msg_type is None:
            return None
        if msg_type == CommonMSG.MSG_RF_RADAR_DATA:
            self.runningave.add_clresp(clresp)
            ret_data = self.runningave.get_runningave()
            self.logger.debug("Returning radar data {}".format(ret_data))
        elif msg_type == CommonMSG.MSG_RF_STOCK_DATA:
            if ret_code == commlink.BaseCommLink.RC_NO_TAGS or\
               ret_code == commlink.BaseCommLink.RC_NO_BARCODE:
                # the scan event failed to return any EPC or barcode data
                # ->we return an empty list
                ret_data = []
            else:
                ret_data = clresp[commlink.EP_VAL]
        elif msg_type == CommonMSG.MSG_RF_CMD_RESP:
            ret_data = clresp.rl
        # do something with ret_data here and return a CommonMSG or None
        if ret_data is None:
            return None
        assert msg_type is not None and ret_data is not None, "convert_message error 99"
        return CommonMSG(msg_type, ret_data)

    # stocky main server messaging service....
    def generate_msg(self) -> typing.Optional[CommonMSG]:
        """Block and return a message to the web server
        Typically, when the user presses the trigger of the RFID reader,
        we will send a message with the scanned data back.
        NOTE: this method is overrulling the method defined in BaseTaskMeister.
        """
        clresp: commlink.CLResponse = self._cl.raw_read_response()
        # print("INCOMING {}".format(clresp))
        return self._convert_message(clresp)

    def set_region(self, region_code: str) -> None:
        """Set the geographic region of the RFID reader.
        Examples of this are 'us', 'eu', 'tw', etc.
        NOTE: not all 1128 readers support this command and will return and error message
        instead.
        """
        if len(region_code) != 2:
            raise RuntimeError("length of region code <> 2!")
        cmdstr = ".sr -s {}".format(region_code)
        self._sendcmd(cmdstr)

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
        cmdstr = ".al -b{} -v{} -d{} -t{} -n\n".format(onoffdct[p.buzzeron],
                                                       onoffdct[p.vibrateon],
                                                       p.vblen.value,
                                                       p.pitch.value)
        self._sendcmd(cmdstr)

    def get_alert_default(self) -> AlertParams:
        """Return the current default alert parameters."""
        raise NotImplementedError('not implemented')

    def abort(self) -> None:
        """Abort the current command."""
        cmdstr = ".ab\n"
        self._sendcmd(cmdstr)

    def set_readbarcode_params(self, p: BarcodeParams) -> None:
        cmdstr = ".bc " + p.tostr() + " -n\n"
        self._sendcmd(cmdstr, "bcparams")

    def get_readbarcode_params(self) -> BarcodeParams:
        raise NotImplementedError('not implemented')

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
        self._sendcmd(cmdstr, "setbt")

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
        self._sendcmd(cmdstr, "settime")

        if yy < 2000:
            raise RuntimeError("year is out of range")
        if not (1 <= mm <= 12):
            raise RuntimeError("month is out of range")
        if not (1 <= dd <= 31):
            raise RuntimeError("day is out of range")
        cmdstr = ".da -s {:02d}{:02d}{:02d}".format(yy-2000, mm, dd)
        self._sendcmd(cmdstr, "setdate")

    def reset_inventory_options(self):
        """Issue a command to reset the .iv options to the default ones."""
        self._sendcmd(".iv -x", "IVreset")

    def RadarSetup(self, EPCcode: str) -> None:
        """Set up the reader to search for a tag with a specific Electronic Product Code (EPC).
        by later on issuing RadarGet() commands.
        The 'Radar' functionality allows the user to search for a specific tag, and to determine
        its distance from the reader using the RSS (return signal strength) field.

        See the TLS document: 'Application\ Note\ -\ Advice\ for\ Implementing\ a\ Tag\ Finder\ Feature\ V1.0.pdf'
        """
        # cmdstr = ".iv -x -n -ron -io off -qt b -qs s0 -sa 4 -st s0 -sb epc -sd {} -sl 30 -so 0020".format(EPCcode)
        self.reset_inventory_options()
        cmdstr = ".iv -al off -x -n -fi on -ron -io off -qt b -qs s0 -sa 4 -st s0 -sl 30 -so 0020"
        self._sendcmd(cmdstr, "radarsetup")

    def RadarGet(self) -> None:
        """Issue a command to get the RSSI value of the tag previously selected
        by its EPC in RadarSetup.
        The response will be available on the response queue."""
        self._sendcmd(".iv", comment='RAD')

    def BT_set_stock_check_mode(self):
        """Set the RFID reader into stock taking mode."""
        self.reset_inventory_options()
        alert_parms = AlertParams(buzzeron=False, vibrateon=True,
                                  vblen=BuzzViblen('med'),
                                  pitch=Buzzertone('med'))
        self.doalert(alert_parms)

    def send_RFID_msg(self, msg: CommonMSG) -> None:
        """The stocky server uses this routine to send messages (commands) to the
        RFID reader device."""
        if msg.msg == CommonMSG.MSG_WC_STOCK_CHECK:
            self.mode = tls_mode.stock
            self.BT_set_stock_check_mode()
        elif msg.msg == CommonMSG.MSG_WC_RADAR_MODE:
            self.mode = tls_mode.radar
            self.RadarSetup('000000000000000000001237')
        elif msg.msg == CommonMSG.MSG_SV_GENERIC_COMMAND:
            self.mode = tls_mode.stock
            # self.BT_set_stock_check_mode()
            cmdstr = msg.data
            # print("BLACMD {}".format(cmdstr))
            self._sendcmd(cmdstr, "radarsetup")
        else:
            self.mode = tls_mode.undef
            self.logger.debug("TLS skipping msg {}".format(msg))
