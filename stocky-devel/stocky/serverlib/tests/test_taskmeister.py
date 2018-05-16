
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
        self.sec_interval = 0.1
        self.num_ticks = 3
        self.test_sleep_time = self.sec_interval * self.num_ticks
        self.logger = logging.Logger("testing")
        self.msgq = DummyQueue()

    def perform_timetest(self, taskmeister: Taskmeister.BaseTaskMeister):
        # with ticker disabled, should be no messages
        gevent.sleep(self.test_sleep_time)
        tn = self.msgq.num_messages()
        if tn != 0:
            raise RuntimeError("unexpected tn = {}".format(tn))
        # now switch the ticker on
        taskmeister.set_active(True)
        gevent.sleep(self.test_sleep_time)
        tn = self.msgq.num_messages()
        print("after sleep {}".format(tn))
        if tn != self.num_ticks:
            raise RuntimeError("unexpected tn = {}".format(tn))
        # assert False, "force fail"

    def test_tick01(self) -> None:
        """TickGenerator must generate ticks when enabled"""
        testname = "hello"
        ticker = Taskmeister.TickGenerator(self.msgq, self.logger,
                                           self.sec_interval, testname)
        self.perform_timetest(ticker)

    def test_random01(self) -> None:
        """RandomGenerator must generate messages when enabled"""
        rand = Taskmeister.RandomGenerator(self.msgq, self.logger,
                                           self.sec_interval)
        self.perform_timetest(rand)

    def test_base01(self) -> None:
        tt1 = Taskmeister.BaseTaskMeister(self.msgq, self.logger, 1)
        tt2 = Taskmeister.BaseReader(self.msgq, self.logger)
        for tt in [tt1, tt2]:
            with pytest.raises(NotImplementedError):
                tt.generate_msg()

    def test_listgen01(self) -> None:
        testlist = ['one', 'two', '', 'three']
        tt = Taskmeister.CommandListGenerator(self.msgq,
                                              self.logger,
                                              self.sec_interval,
                                              "testy",
                                              testlist)
        tt.set_active(True)
        test_sleep_time = self.sec_interval * len(testlist)
        gevent.sleep(test_sleep_time)
        gotlst = self.msgq.msglst
        # check length...
        expected_lst = [d for d in testlist if d != '']
        assert len(gotlst) == len(expected_lst), "wrong list length"
        # check the actual data...
        gotmsglst = [r.data for r in gotlst]
        assert gotmsglst == expected_lst, "lists are not the same!"

    def test_listgen02(self) -> None:
        testlist = []
        with pytest.raises(RuntimeError):
            Taskmeister.CommandListGenerator(self.msgq,
                                             self.logger,
                                             self.sec_interval,
                                             "testy",
                                             testlist)
