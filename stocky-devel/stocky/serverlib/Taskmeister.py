

# a generic class that defines an interface to gevent job tasks
# a Taskmeister has a gevent loop which, when active, puts CommonMSG instances onto
# a message queue

import typing
from random import random
import pathlib

import gevent
import gevent.queue
from webclient.commonmsg import CommonMSG

import serverlib.ServerWebSocket as WS


# NOTE: It is important that sec_interval, the time that a task sleeps, is strictly larger
# than zero. If this is not the case, starvation of other tasks will occur.
# This can lead to errors that are difficult to find. Specifically, a message
# that a WebSocket reader passes up the chain by the queue will never be acted on
# by its consumers because they will not be able to dequeue the message due to starvation.
MIN_SEC_INTERVAL = 0.01


class DelayTaskMeister:
    """Put a designated message on the queue after a specified delay
    every time the class is triggered.
    """
    def __init__(self, msgQ: gevent.queue.Queue,
                 logger,
                 sec_interval: float,
                 msg_tosend: CommonMSG) -> None:
        self.msgQ = msgQ
        self.logger = logger
        self._sec_sleep = sec_interval
        self.msg_tosend = msg_tosend

    def trigger(self) -> None:
        gevent.spawn(self._worker_one_shot)

    def _worker_one_shot(self) -> None:
        gevent.sleep(self._sec_sleep)
        self.msgQ.put(self.msg_tosend)


class BaseTaskMeister:
    def __init__(self, msgQ: gevent.queue.Queue,
                 logger,
                 sec_interval: float) -> None:
        self.msgQ = msgQ
        self.logger = logger
        self._isactive = False
        self._sec_sleep = max(sec_interval, MIN_SEC_INTERVAL)
        self._do_main_loop = True
        gevent.spawn(self._worker_loop)

    def set_active(self, is_active: bool) -> None:
        """Enable/ disable the scheduling of messages"""
        self._isactive = is_active

    def _worker_loop(self) -> None:
        """The Taskmeister event generation loop.
        If we are active, we put non-None messages onto the provided message queue
        that self.generate_msg() has created, then sleep for the required time.
        """
        msgq = self.msgQ
        while self._do_main_loop:
            if self._isactive:
                msg = self.generate_msg()
                if msg is not None:
                    # print("enqueueing {}".format(msg))
                    msgq.put(msg)
            # --
            gevent.sleep(self._sec_sleep)

    def _SetTaskFinished(self) -> None:
        """Cause the worker loop to terminate."""
        self._do_main_loop = False

    def generate_msg(self) -> typing.Optional[CommonMSG]:
        """Generate a message for this class.
        This routine may block or take as long as it likes.
        It may return None if a message is not meant to be passed back onto the queue.
        Overwrite this method in the subclasses.
        """
        raise NotImplementedError("generate_msg: not implemented")


class FileChecker(BaseTaskMeister):
    """Check for existence of a given file every X seconds, generating a message
    when the state changes.
    """
    def __init__(self, msgQ: gevent.queue.Queue,
                 logger,
                 sec_interval: float,
                 do_activate: bool, file_to_check: str) -> None:
        super().__init__(msgQ, logger, sec_interval)
        self._path = pathlib.Path(file_to_check)
        self._curstate: typing.Optional[bool] = None
        if do_activate:
            self.set_active(True)

    def file_exists(self) -> bool:
        return self._path.exists()

    def generate_msg(self) -> typing.Optional[CommonMSG]:
        """Generate a message for this class.
        This routine may block or take as long as it likes.
        It may return None if a message is not meant to be passed back onto the queue.
        Overwrite this method in the subclasses.
        """
        newstate = self.file_exists()
        if self._curstate != newstate:
            self._curstate = newstate
            return CommonMSG(CommonMSG.MSG_SV_FILE_STATE_CHANGE, newstate)
        else:
            return None


class BaseReader(BaseTaskMeister):
    """A BaseReader is a BaseTaskMeister class that is automatically
    activated upon instantiation, and waits sec_interval seconds in the main loop between reads.
    The main purpose of this class is for handling blocking reads (websockets, bluetooth, ...)
    """
    def __init__(self, msgQ: gevent.queue.Queue,
                 logger,
                 sec_interval: float,
                 do_activate: bool) -> None:
        super().__init__(msgQ, logger, sec_interval)
        if do_activate:
            self.set_active(True)


class RandomGenerator(BaseTaskMeister):
    """Generate a random number message every X seconds. This is used for testing."""
    def generate_msg(self) -> typing.Optional[CommonMSG]:
        number = round(random()*10, 3)
        self.logger.debug("random: {}".format(number))
        return CommonMSG(CommonMSG.MSG_SV_RAND_NUM, number)


class TickGenerator(BaseTaskMeister):
    """Generate a timer message every X seconds.
    The timer message contains the name (msgid) of the timer event.
    """
    def __init__(self, msgQ: gevent.queue.Queue, logger,
                 sec_interval: float, msgid: str) -> None:
        super().__init__(msgQ, logger, sec_interval)
        self.msgid = msgid

    def generate_msg(self) -> typing.Optional[CommonMSG]:
        return CommonMSG(CommonMSG.MSG_SV_TIMER_TICK, self.msgid)


class CommandListGenerator(TickGenerator):
    """Generate a generic message every X seconds.
    The commands are cycled through from a list of commands provided.
    An empty string in the list means that that cycle is skipped.
    """
    def __init__(self, msgQ: gevent.queue.Queue, logger,
                 sec_interval: float, msgid: str,
                 cmdlst: typing.List[str]) -> None:
        super().__init__(msgQ, logger, sec_interval, msgid)
        self.cmdlst = cmdlst
        if len(cmdlst) == 0:
            raise ValueError("cmdlst len is 0")
        self.nmsg = 0

    def generate_msg(self) -> typing.Optional[CommonMSG]:
        cmdstr = self.cmdlst[self.nmsg]
        self.nmsg = (self.nmsg + 1) % len(self.cmdlst)
        if len(cmdstr) == 0:
            return None
        return CommonMSG(CommonMSG.MSG_SV_GENERIC_COMMAND, cmdstr)


class WebSocketReader(BaseReader):
    """The stocky server uses this Taskmeister to receive messages from the webclient
    in json format. It puts CommonMSG instances onto the queue."""

    def __init__(self, msgQ: gevent.queue.Queue,
                 logger,
                 ws: WS.BaseWebSocket,
                 sec_interval: float=0.0,
                 do_activate: bool=True) -> None:
        self.ws = ws
        super().__init__(msgQ, logger, sec_interval, do_activate)

    def generate_msg(self) -> typing.Optional[CommonMSG]:
        """Block until a command is received from the webclient over websocket.
        Return the JSON string received as a CommonMSG instance."""
        dct = self.ws.receiveMSG()
        if dct is None:
            self.logger.error("received None over ws, returning None")
            retmsg = None
        elif isinstance(dct, dict):
            need_keys = frozenset(['msg', 'data'])
            got_keys = set(dct.keys())
            if need_keys <= got_keys:
                # now make sure we have a legal msg field
                try:
                    retmsg = CommonMSG(dct['msg'], dct['data'])
                except (ValueError, TypeError) as e:
                    self.logger.error("illegal msgtype= '{}'".format(dct['msg']))
                    retmsg = None
                xtra_keys = got_keys - need_keys
                if xtra_keys:
                    self.logger.warn("unexpected extra dict keys, got '{}'".format(got_keys))
            else:
                self.logger.error("unknown keys in {}".format(got_keys))
                retmsg = None
        else:
            raise RuntimeError("unexpected message {}".format(dct))
        #
        if retmsg is not None and retmsg.msg == CommonMSG.MSG_WC_EOF:
            self._SetTaskFinished()
        mmm = "WS.generate_msg returning commonmsg {}".format(retmsg)
        self.logger.debug(mmm)
        # print(mmm)
        return retmsg
