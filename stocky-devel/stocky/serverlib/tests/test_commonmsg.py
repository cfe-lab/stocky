
import typing
import pytest
from webclient.commonmsg import CommonMSG


class Test_commonmsg:

    def test_commonmsg00(self):
        """Sanity check the MSG names...
        and check we can instantiate all message types."""
        msglst = CommonMSG.valid_msg_lst
        msgdct = CommonMSG.valid_msg_dct
        # names must be unique
        assert len(msglst) == len(msgdct), "unexpected dct length"

        # names must allow assignment to exactly one source.
        mydat = 100.0
        for msgtype in msglst:
            c = CommonMSG(msgtype, mydat)
            assert isinstance(c, CommonMSG), "expected a CommonMSG"
            assert c.msg == msgtype, "wrong type"
            assert c.data == mydat, "wrong data"

            nn = sum([c.is_from_server(), c.is_from_webclient(), c.is_from_rfid_reader()])
            assert nn == 1, "illegal name {}".format(msgtype)

    def test_commonmsg01(self):
        """Check illegal msgtypes are caught."""
        mydat = 100.0
        # wrong type or value should raise an appropriate assertion
        for msg, exc in [([1, 2], TypeError),
                         ("blastr", ValueError)]:
            with pytest.raises(exc):
                CommonMSG(msg, mydat)
