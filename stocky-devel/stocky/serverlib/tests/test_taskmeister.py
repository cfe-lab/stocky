import typing
import pytest
import gevent
import geventwebsocket.exceptions
import logging
import tempfile

import serverlib.Taskmeister as Taskmeister
import serverlib.qai_helper as qai_helper
import serverlib.ServerWebSocket as ServerWebSocket

from webclient.commonmsg import CommonMSG


class DummyQueue:
    """A dummy message queue for testing"""
    def __init__(self):
        self.msglst = []

    def reset(self) -> None:
        self.msglst = []

    def put(self, msg: CommonMSG) -> None:
        assert isinstance(msg, CommonMSG), "attempted to add non CommomMSG msg!"
        self.msglst.append(msg)

    def num_messages(self):
        return len(self.msglst)


class DummyWebsocket:
    def __init__(self, sec_interval: float, data: typing.Any) -> None:
        self.sec_interval = sec_interval
        self._set_data(data)

    def _set_data(self, data: typing.Any=None) -> None:
        self.retdat: typing.Optional[bytes] = None if data is None else bytes(qai_helper.tojson(data), 'utf-8')

    def _set_json_val(self, newjson: bytes) -> None:
        assert isinstance(newjson, bytes), 'set_json must be bytes'
        self.retdat = newjson

    def receive(self) -> bytes:
        assert isinstance(self.retdat, bytes), 'receive: must be bytes'
        gevent.sleep(self.sec_interval)
        return self.retdat


class ExceptionDummyWebsocket(DummyWebsocket):

    def receive(self) -> bytes:
        raise geventwebsocket.exceptions.WebSocketError('hello from the dummy!')


class Test_Taskmeister:

    def setup_method(self) -> None:
        self.sec_interval = 0.1
        self.num_ticks = 3
        self.test_sleep_time = self.sec_interval * self.num_ticks
        self.logger = logging.Logger("testing")
        self.msgq = DummyQueue()

    def test_delay01(self) -> None:
        """Perform test of a DelayTaskMeister"""
        tn = self.msgq.num_messages()
        if tn != 0:
            raise RuntimeError("unexpected tn = {}".format(tn))
        msg = CommonMSG(CommonMSG.MSG_SV_RAND_NUM, 'delaytest')
        d = Taskmeister.DelayTaskMeister(self.msgq, self.logger,
                                         self.sec_interval, msg)
        d.trigger()
        gevent.sleep(self.test_sleep_time)
        tn = self.msgq.num_messages()
        if tn != 1:
            raise RuntimeError("unexpected tn = {}".format(tn))

    def test_filechecker01(self) -> None:
        checkfile = tempfile.NamedTemporaryFile()
        checkfilename = checkfile.name
        ft = Taskmeister.FileChecker(self.msgq, self.logger,
                                     self.sec_interval, True, checkfilename)
        assert ft is not None, "ft is None"
        gevent.sleep(self.test_sleep_time)
        tn = self.msgq.num_messages()
        print("after sleep 1 {}".format(tn))
        if tn != 1:
            raise RuntimeError("unexpected tn = {}".format(tn))
        # now close the checkfile to remove it
        checkfile.close()
        gevent.sleep(self.test_sleep_time)
        tn = self.msgq.num_messages()
        print("after sleep 2 {}".format(tn))
        if tn != 2:
            raise RuntimeError("unexpected tn = {}".format(tn))

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
                                           self.sec_interval, False)
        self.perform_timetest(rand)

    def test_base01(self) -> None:
        tt1 = Taskmeister.BaseTaskMeister(self.msgq, self.logger, 1, False)
        # tt2 = Taskmeister.BaseReader(self.msgq, self.logger, 1, False)
        # for tt in [tt1, tt2]:
        for tt in [tt1]:
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
        testlist: typing.List[str] = []
        with pytest.raises(ValueError):
            Taskmeister.CommandListGenerator(self.msgq,
                                             self.logger,
                                             self.sec_interval,
                                             "testy",
                                             testlist)

    def test_wsreader01(self):
        """The WebSocketReader must behave sensibly when it reads
        junk from the websocket, and also produce a message on good data.
        """
        rawws = DummyWebsocket(self.sec_interval, None)
        ws = ServerWebSocket.JSONWebSocket(rawws, self.logger)
        wsr = Taskmeister.WebSocketReader(self.msgq,
                                          self.logger,
                                          ws,
                                          sec_interval=1.0,
                                          do_activate=False)
        assert wsr is not None, "wsr is None!"
        ok_dct = {'msg': CommonMSG.MSG_SV_RAND_NUM, 'data': 'dolly'}
        extra_dct = {'msg': CommonMSG.MSG_SV_RAND_NUM, 'data': 'dolly', 'extra': 'message'}
        ok_msg = CommonMSG(ok_dct['msg'], ok_dct['data'])
        for faulty_data, doraw, exp_val in [({'bla': 'blu'}, True, None),
                                            ({'msg': 'hello'}, True, None),
                                            ([1, 2, 3], True, None),
                                            (b'[1, 2}', False, None),
                                            ({'msg': 'hello', 'data': 'dolly'}, True, None),
                                            ([1, 2, 3], True, None),
                                            (extra_dct, True, ok_msg),
                                            (ok_dct, True, ok_msg)]:
            if doraw:
                rawws = DummyWebsocket(self.sec_interval, faulty_data)
            else:
                rawws = DummyWebsocket(self.sec_interval, None)
                rawws._set_json_val(faulty_data)
            ws = ServerWebSocket.JSONWebSocket(rawws, self.logger)
            wsr.ws = ws
            retmsg = wsr.generate_msg()
            print("after sleep exp: {}, got {}".format(exp_val, retmsg))
        # assert False, "force fail"

    def test_wsreader02(self):
        """The WebSocketReader must behave sensibly when websocket.read()
        raises an exception.
        We expect an EOF message when the underlying websocket raises an exception on read.
        """
        rawws = ExceptionDummyWebsocket(self.sec_interval, None)
        ws = ServerWebSocket.JSONWebSocket(rawws, self.logger)
        wsr = Taskmeister.WebSocketReader(self.msgq,
                                          self.logger,
                                          ws,
                                          sec_interval=1.0,
                                          do_activate=False)
        exp_msg_val = CommonMSG.MSG_WC_EOF
        retmsg = wsr.generate_msg()
        print("after sleep exp: {}, got {}".format(exp_msg_val, retmsg))
        assert exp_msg_val == retmsg.msg, "unexpected retmsg"
        # assert False, "force fail"
