"""A collection of classes that define an interface to :py:mod:`gevent` job tasks.
   A Taskmeister has a gevent loop which, when active, puts :py:class:`CommonMSG`
   instances onto a message queue.
"""

import typing
import random
import pathlib

import gevent
import gevent.queue
import gevent.subprocess as subprocess
from webclient.commonmsg import CommonMSG

import serverlib.ServerWebSocket as WS


# NOTE: It is important that sec_interval, the time that a task sleeps, is strictly larger
# than zero. If this is not the case, starvation of other tasks will occur.
# This can lead to errors that are difficult to find. Specifically, a message
# that a WebSocket reader passes up the chain by the queue will never be acted on
# by its consumers because they will not be able to dequeue the message due to starvation.
MIN_SEC_INTERVAL = 0.1
# MIN_SEC_INTERVAL = 0.6


class LoggingMixin:
    """A Mixin class that can handle logging.
    Using gevents, logging to files can be difficult to decipher.
    This class allows logging reports of certain instances
    to be printed directly to terminal rather than logged.
    This is achieved by setting a self._lverb = True
    """

    def __init__(self, logger) -> None:
        self._logger = logger

    def is_verbose(self) -> bool:
        """Return: this logger is currently in verbose mode"""
        return hasattr(self, "_lverb") and self._lverb

    def _log_error(self, msg: str) -> None:
        if self.is_verbose():
            print(msg)
        else:
            self._logger.error(msg)

    def _log_debug(self, msg: str) -> None:
        if self.is_verbose():
            print(msg)
        else:
            self._logger.debug(msg)

    def _log_warning(self, msg: str) -> None:
        if self.is_verbose():
            print(msg)
        else:
            self._logger.warning(msg)


class DelayTaskMeister(LoggingMixin):
    """Put a designated message on the queue after a specified delay
    every time the class is triggered.
    """
    def __init__(self, msg_q: gevent.queue.Queue,
                 logger,
                 sec_interval: float,
                 msg_tosend: CommonMSG) -> None:
        """
        Args:
           msq_q: the queue to put messages onto.
           logger: a logging instance to use for logging.
           sec_interval: the time to wait after triggering before putting a message on the queue
           msg_tosend: the message to put on the queue.
        """
        super().__init__(logger)
        self.msg_q = msg_q
        self._sec_sleep = sec_interval
        self.msg_tosend = msg_tosend

    def trigger(self) -> None:
        """Trigger the DelayTaskMeister.
        After calling this method, the instance's message will be put on the queue
        after the prescribed interval.
        """
        gevent.spawn(self._worker_one_shot)

    def _worker_one_shot(self) -> None:
        gevent.sleep(self._sec_sleep)
        self.msg_q.put(self.msg_tosend)


class DaemonTaskMeister(LoggingMixin):
    """Run a specified shell command, and restart it after a delay whenever it has exited.
    """
    STATUS_UNDEF = -1
    STATUS_RUNNING = 0
    STATUS_CONFIG_ERROR = 1
    STATUS_COMMAND_FAILED = 2
    STATUS_STOPPED = 3
    STATUS_COMPLETED = 4

    def __init__(self, logger, command: str, sec_interval: int) -> None:
        super().__init__(logger)
        self._lverb = False
        self.cmdstr = command
        self.cmdlst = command.split()
        self._sec_sleep = max(sec_interval, MIN_SEC_INTERVAL)
        self.curstat = self.STATUS_UNDEF
        self.do_run = True
        self.proc = None
        self.numchecks = 0
        # NOTE: I should launch the command here, THEN spawn off the checker loop
        # i.e. the checker loop must NOT spawn off the command itself...
        self._launch_cmd()
        self.greenlet = gevent.spawn(self._dorun)
        # self._dorun()

    def _launch_cmd(self) -> None:
        if self.curstat == self.STATUS_CONFIG_ERROR:
            return
        try:
            self.proc = subprocess.Popen(self.cmdlst, shell=False)
            self.curstat = self.STATUS_RUNNING
        except FileNotFoundError as err:
            self.curstat = self.STATUS_CONFIG_ERROR
            self._log_error("command '{}' config error: {}".format(self.cmdlst, err))
        self.numchecks = 0

    def get_status(self) -> int:
        """Return the current status of the Taskmeister."""
        return self.curstat

    def stop_cmd(self, do_wait: bool = False) -> None:
        """Stop the command without restarting it"""
        self.do_run = False
        self._do_kill()
        if do_wait:
            self.greenlet.join()
        self.curstat = self.STATUS_STOPPED

    def stop_and_restart_cmd(self) -> None:
        """Stop the command if it is running, then restart it again"""
        # NOTE: just kill the job. _dorun will restart it
        self._do_kill()

    def _do_kill(self) -> None:
        if self.proc is not None:
            self.proc.kill()
            self.proc.wait()
            self.proc = None

    def _dorun(self) -> None:
        while self.do_run:
            self._log_debug("***check daemon '{}'".format(self.cmdstr))
            if self.proc is None:
                self._log_debug("launch --")
                self._launch_cmd()
            gevent.sleep(self._sec_sleep)
            if self.proc is not None:
                retcode = self.proc.poll()
                self.numchecks += 1
                if retcode is None:
                    # the command is still running...
                    self._log_debug("cmd still running...")
                else:
                    err_str = "***cmd '{}' exited with retcode {}".format(self.cmdstr, retcode)
                    self._log_error(err_str)
                    self.proc = None
                    if retcode == 0:
                        self.curstat = self.STATUS_COMPLETED
                    else:
                        self.curstat = self.STATUS_COMMAND_FAILED
            self._log_debug("loop curstat: {}, do_run: {}".format(self.curstat, self.do_run))
        # shut down nicely...
        self._log_debug("***Daemon exiting...")
        self._do_kill()


class BaseTaskMeister(LoggingMixin):
    "A fundamental TaskMeister class."

    def __init__(self, msg_q: gevent.queue.Queue,
                 logger,
                 sec_interval: float,
                 is_active: bool) -> None:
        """
        Upon instantiation, this class spawns off its mainloop using :mod:`gevent`.

        Args:
           msqG: the queue to put messages onto.
           logger: a logging instance to use for logging.
           sec_interval: the time to wait between calls to generate_msg in the event loop.
           is_active: whether to set the class active upon instantiation.\
           The active state can be changed at a later time with :meth:`set_active` .

        The mainloop essentially does::

         while self._do_main_loop:
             if self._isactive:
                 msg = self.generate_msg()
                 if msg is not None:
                     msgq.put(msg)
             # --
             gevent.sleep(self._sec_sleep)

        Where :meth:`generate_msg` is overridden in subclasses.
        """
        self.msg_q = msg_q
        super().__init__(logger)
        self._isactive = is_active
        self._sec_sleep = max(sec_interval, MIN_SEC_INTERVAL)
        self._do_main_loop = True
        self._greenlet = gevent.spawn(self._worker_loop)

    def set_active(self, is_active: bool) -> None:
        """Enable/disable the scheduling of messages.

        Args:
           is_active: the new value of is_active to set.
        """
        self._isactive = is_active

    def _worker_loop(self) -> None:
        """The Taskmeister event generation loop.
        If we are active, we put non-None messages onto the provided message queue
        that self.generate_msg() has created, then sleep for the required time.
        """
        msgq = self.msg_q
        while self._do_main_loop:
            if self._isactive:
                msg = self.generate_msg()
                if msg is not None:
                    # print("enqueueing {}".format(msg))
                    msgq.put(msg)
            # --
            gevent.sleep(self._sec_sleep)

    def _set_task_finished(self) -> None:
        """Cause the worker loop to terminate."""
        self._do_main_loop = False

    def generate_msg(self) -> typing.Optional[CommonMSG]:
        """Generate a message for this class.
        This routine may block or take as long as it likes.
        It may return None if a message is not meant to be passed back onto the queue.
        Overwrite this method in the subclasses.

        Raises:
           NotImplementedError: when called.
        """
        raise NotImplementedError("generate_msg: not implemented")


class FileChecker(BaseTaskMeister):
    """Check for the existence of a specified file every sec_interval seconds, generating
    a message when the state changes.
    """
    def __init__(self, msg_q: gevent.queue.Queue,
                 logger,
                 sec_interval: float,
                 do_activate: bool,
                 file_to_check: str) -> None:
        """This class is typically used to monitor removable files and devices
        such as USB devices.

        Args:
           msqG: the queue to put messages onto.
           logger: a logging instance to use for logging.
           sec_interval: the time to wait between calls to generate_msg in the event loop.
           do_activate: whether to set the class active upon instantiation.
           file_to_check: the name of the file to monitor.
        """
        super().__init__(msg_q, logger, sec_interval, do_activate)
        self._path = pathlib.Path(file_to_check)
        self._curstate: typing.Optional[bool] = None

    def file_exists(self) -> bool:
        """Return whether the file exists."""
        return self._path.exists()

    def generate_msg(self) -> typing.Optional[CommonMSG]:
        """
        Generate a message if the monitored file has appeared or disappeared
        since the last call.
        """
        newstate = self.file_exists()
        if self._curstate != newstate:
            self._curstate = newstate
            return CommonMSG(CommonMSG.MSG_SV_FILE_STATE_CHANGE, newstate)
        return None


class RandomGenerator(BaseTaskMeister):
    """Generate a random number message every sec_interval seconds. This is used for testing."""
    def generate_msg(self) -> typing.Optional[CommonMSG]:
        number = round(random.random()*10, 3)
        self._log_debug("random: {}".format(number))
        return CommonMSG(CommonMSG.MSG_SV_RAND_NUM, number)


class TickGenerator(BaseTaskMeister):
    """Generate a timer message every sec_interval seconds.
    The timer message contains the name (msgid) of the timer event.
    """
    def __init__(self, msg_q: gevent.queue.Queue, logger,
                 sec_interval: float, msgid: str) -> None:
        super().__init__(msg_q, logger, sec_interval, False)
        self.msgid = msgid

    def generate_msg(self) -> typing.Optional[CommonMSG]:
        return CommonMSG(CommonMSG.MSG_SV_TIMER_TICK, self.msgid)


class CommandListGenerator(TickGenerator):
    """Generate a generic message every sec_interval seconds.
    The commands are cycled through from a list of commands provided.
    An empty string in the list means that that cycle is skipped.
    This class is used for testing.
    """
    def __init__(self, msg_q: gevent.queue.Queue, logger,
                 sec_interval: float, msgid: str,
                 cmdlst: typing.List[str]) -> None:
        super().__init__(msg_q, logger, sec_interval, msgid)
        self.cmdlst = cmdlst
        if not cmdlst:
            raise ValueError("cmdlst is empty")
        self.nmsg = 0

    def generate_msg(self) -> typing.Optional[CommonMSG]:
        cmdstr = self.cmdlst[self.nmsg]
        self.nmsg = (self.nmsg + 1) % len(self.cmdlst)
        return CommonMSG(CommonMSG.MSG_SV_GENERIC_COMMAND, cmdstr) if cmdstr else None


class WebSocketReader(BaseTaskMeister):
    """The stocky server uses this Taskmeister to receive messages from the webclient
    in json format. It puts CommonMSG instances onto the queue."""

    def __init__(self, msg_q: gevent.queue.Queue,
                 logger,
                 ws: WS.BaseWebSocket,
                 sec_interval: float = 0.0,
                 do_activate: bool = True) -> None:
        """
        Args:
           msq_q: the queue to put messages onto.
           logger: a logging instance to use for logging.
           ws: the websocket to read from.
           sec_interval: the time to wait between calls to generate_msg in the event loop.
           is_active: whether to set the class active upon instantiation.\
           The active state can be changed at a later time with :meth:`set_active` .
        """
        self.ws = ws
        super().__init__(msg_q, logger, sec_interval, do_activate)

    def generate_msg(self) -> typing.Optional[CommonMSG]:
        """Block until a data message is received from the webclient over websocket
        in JSON format.
        The resulting python data structure is analysed. If it is a valid message
        as defined in :mod:`webclient.commonmsg` , it is put on the queue as
        a CommonMSG instance.
        """
        lverb = True
        if lverb:
            print("WSGM: before rec msg")
        dct = self.ws.receiveMSG()
        if lverb:
            print("WSGM: received msg")
        # the return value is either None or a dict.
        if dct is None:
            self._log_error("received None over ws, returning None")
            retmsg = None
        elif isinstance(dct, dict):
            need_keys = frozenset(['msg', 'data'])
            got_keys = set(dct.keys())
            if need_keys <= got_keys:
                # now make sure we have a legal msg field
                try:
                    retmsg = CommonMSG(dct['msg'], dct['data'])
                except (ValueError, TypeError):
                    self._log_error("illegal msgtype= '{}'".format(dct['msg']))
                    retmsg = None
                xtra_keys = got_keys - need_keys
                if xtra_keys:
                    self._log_warning("unexpected extra dict keys, got '{}'".format(got_keys))
            else:
                self._log_error("unknown keys in {}".format(got_keys))
                retmsg = None
        #
        if retmsg is not None and retmsg.msg == CommonMSG.MSG_WC_EOF:
            self._set_task_finished()
        mmm = "WebSocketReader.generate_msg returning commonmsg..."
        self._log_debug(mmm)
        print(mmm)
        return retmsg


class RandomRFIDScanner(BaseTaskMeister):
    """Generate spoofed CommonMSG.MSG_RF_CMD_RESP messages at regular intervals
    just as if the data was coming from a RFID reader scan.
    Barcode scans a RFID scans are produced with equal probability.
    This class holds a list of predefined RFID labels.
    In the case of a barcode scan, a single RFID label is chosen randomly
    from this list to be returned.
    In the case of an RFID scan, a random number of random RFID labels
    are returned.
    This class is used for mocking a server for the QAI client to directly query.
    """
    def __init__(self, msg_q: gevent.queue.Queue,
                 logger,
                 sec_interval: float) -> None:
        super().__init__(msg_q, logger, sec_interval, False)
        self.taglst = ["CHEM{}".format(11000+i) for i in range(20)]

    def generate_msg(self) -> typing.Optional[CommonMSG]:
        # generate either a barcode or RFID scan ?
        do_barcode = random.random() < 0.5
        if do_barcode:
            nselect = 1
            prelim = ['CS', '.bc,']
        else:
            # RFID scan
            nselect = random.randrange(len(self.taglst))
            prelim = ['CS', '.iv,']
        sel_tags = random.choices(self.taglst, k=nselect)
        scan_data = [prelim] + [['EP', tag] for tag in sel_tags] + [['OK', '']]
        print("returning: '{}'".format(scan_data))
        return CommonMSG(CommonMSG.MSG_RF_CMD_RESP, scan_data)
