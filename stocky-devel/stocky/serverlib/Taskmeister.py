

# a generic class that defines interfaces to job tasks
import typing
from random import random

import gevent
import gevent.queue
from geventwebsocket import websocket
import geventwebsocket.exceptions

from webclient.commonmsg import CommonMSG

import serverlib.QAILib as QAILib


class BaseTaskMeister:
    def __init__(self, msgQ: gevent.queue.Queue,
                 logger,
                 sec_interval: float) -> None:
        self.msgQ = msgQ
        self.logger = logger
        self._isactive = False
        self._sec_sleep = sec_interval
        gevent.spawn(self._worker_loop)

    def set_active(self, is_active: bool) -> None:
        """Enable/ disable the scheduling of messages"""
        self._isactive = is_active

    def _worker_loop(self) -> None:
        msgq = self.msgQ
        while True:
            if self._isactive:
                msg = self.generate_msg()
                if msg is not None:
                    msgq.put(msg)
            # --
            if self._sec_sleep > 0:
                gevent.sleep(self._sec_sleep)

    def generate_msg(self) -> typing.Optional[CommonMSG]:
        """Generate a message for this class.
        This routine may block or take as long as it likes.
        It may return None if a message is not meant to be passed back onto the queue.
        Overwrite this method in the subclasses.
        """
        raise NotImplementedError("generate_msg: not implemented")


class BaseReader(BaseTaskMeister):
    """A BaseReader is a BaseTaskMeister class that is automatically
    activated upon instantiation, and waits sec_interval=0 seconds in the main loop.
    The main purpose of this class is for handling blocking reads (websockets, bluetooth, ...)
    """
    def __init__(self, msgQ: gevent.queue.Queue, logger) -> None:
        super().__init__(msgQ, logger, 0)
        self.set_active(True)


class RandomGenerator(BaseTaskMeister):
    """Generate a random message every second. This is used for testing."""
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
            raise RuntimeError("cmdlst len is 0")
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
    def __init__(self, msgQ: gevent.queue.Queue, logger, ws: websocket) -> None:
        super().__init__(msgQ, logger)
        self.ws = ws

    def generate_msg(self) -> typing.Optional[CommonMSG]:
        """Block until a command is received from the webclient over websocket.
        Return the JSON string received as a CommonMSG instance."""
        try:
            msg = self.ws.receive()
        except geventwebsocket.exceptions.WebSocketError as e:
            self.logger.debug("server received a None: {}".format(e))
            msg = None
        if msg is None:
            retmsg = None
        else:
            dct = QAILib.fromjson(msg)
            retmsg = CommonMSG(dct['msg'], dct['data'])
        return retmsg
