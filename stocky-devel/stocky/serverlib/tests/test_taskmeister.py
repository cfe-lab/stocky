
import pytest
import gevent
import logging

import serverlib.Taskmeister as Taskmeister
# import serverlib.QAILib as QAILib

from webclient.commonmsg import CommonMSG


class DummyQueue:
    """A dummy message queue for testing"""
    def __init__(self):
        self.msglst = []

    def put(self, msg: CommonMSG) -> None:
        assert isinstance(msg, CommonMSG), "attempted to add non CommomMSG msg!"
        self.msglst.append(msg)

    def num_messages(self):
        return len(self.msglst)


class Test_Taskmeister:

    def setup_method(self) -> None:
        self.logger = logging.Logger("testing")
        self.msgq = DummyQueue()

    @pytest.mark.skip(reason="Cannot test with gevent module..")
    def test_tick01(self):
        sec_interval = 1
        testname = "blablahello"
        ticker = Taskmeister.TickGenerator(self.msgq, self.logger,
                                           sec_interval, testname)
        gevent.sleep(3*sec_interval)
        tn = self.msgq.num_messages()
        if tn != 0:
            raise RuntimeError("unexpected tn = {}".format(tn))
        # now switch the ticker on
        ticker.set_active(True)
        gevent.sleep(3*sec_interval)
        tn = self.msgq.num_messages()
        print("after sleep {}".format(tn))
        if tn == 0:
            raise RuntimeError("unexpected tn = {}".format(tn))
        assert False, "force fail"
