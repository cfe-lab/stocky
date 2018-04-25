

# a generic class that defines interfaces to job tasks

from random import random

import gevent
import gevent.queue
from geventwebsocket import websocket

from webclient.commonmsg import CommonMSG

import serverlib.QAILib as QAILib


class BaseTaskMeister:
    def __init__(self, msgQ: gevent.queue.Queue, logger) -> None:
        self.msgQ = msgQ
        self.logger = logger

    def start_job(self) -> None:
        """Start the scheduling of messages"""
        gevent.spawn(self.worker_loop)

    def worker_loop(self) -> None:
        msgq = self.msgQ
        while True:
            msg = self.generate_msg()
            if msg is not None:
                msgq.put(msg)

    def generate_msg(self) -> CommonMSG:
        """Generate this classes messages.
        This routine may block or take as long as it likes.
        Overwrite this method in the subclasses.
        """
        raise NotImplementedError("generate_msg: not implemented")


class RandomGenerator(BaseTaskMeister):
    """Generate a random message every second. This is used for testing."""
    def generate_msg(self) -> CommonMSG:
        number = round(random()*10, 3)
        self.logger.debug("random: {}".format(number))
        gevent.sleep(1)
        return CommonMSG(CommonMSG.MSG_SV_RAND_NUM, number)


class TickGenerator(BaseTaskMeister):
    """Generate a timer message every X seconds.
    The timer message contains the name of the timer event.
    """
    def __init__(self, msgQ: gevent.queue.Queue, logger,
                 sec_interval: int, msgid: str) -> None:
        super().__init__(msgQ, logger)
        self.sec_interval = sec_interval
        self.msgid = msgid
        self._isactive = False

    def set_active(self, is_active: bool) -> None:
        """Enable/ disable the timer """
        self._isactive = is_active

    def generate_msg(self) -> CommonMSG:
        gevent.sleep(self.sec_interval)
        if self._isactive:
            return CommonMSG(CommonMSG.MSG_SV_TIMER_TICK, self.msgid)
        else:
            return None


class WebSocketReader(BaseTaskMeister):
    def __init__(self, msgQ: gevent.queue.Queue, logger, ws: websocket) -> None:
        super().__init__(msgQ, logger)
        self.ws = ws

    def generate_msg(self) -> CommonMSG:
        """Block until a command is received from the webclient over websocket.
        Return the JSON string received as a CommonMSG instance."""
        dct = QAILib.fromjson(self.ws.receive())
        return CommonMSG(dct['msg'], dct['data'])
