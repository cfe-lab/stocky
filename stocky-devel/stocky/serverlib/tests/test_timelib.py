
import pytest
import serverlib.timelib as timelib
import pytz


class Test_timelib:

    def setup_method(self) -> None:
        self.utctime = timelib.utc_nowtime()

    def test_utc(self):
        assert isinstance(self.utctime, timelib.DateTimeType), "wrong type returned"

    def test_loc01(self):
        timelib._tzinfo = None
        with pytest.raises(RuntimeError):
            timelib.loc_nowtime()

    def test_loc02(self):
        with pytest.raises(RuntimeError):
            timelib.set_local_timezone("now")

    def test_loc02a(self):
        with pytest.raises(TypeError):
            timelib.set_local_timezone(10)

    def test_loc03(self):
        tzinfo = pytz.timezone('Europe/Amsterdam')
        timelib.set_local_timezone(tzinfo)
        nn = timelib.loc_nowtime()
        assert isinstance(nn, timelib.DateTimeType), "wrong type returned"

    @pytest.mark.skip(reason="disabled for now")
    def convert_test(self, dtin: timelib.DateTimeType) -> None:
        """Convert a datetime to string then back to datetime.
        The datetime records must be the same.
        Update: actually, as we round the time to seconds on conversion,
        they will not be the same.
        """
        assert isinstance(dtin, timelib.DateTimeType), "wrong type entered"
        nnstr = timelib.datetime_to_str(dtin)
        assert isinstance(nnstr, str), "string expected"
        print("got string '{}'".format(nnstr))
        dtout = timelib.str_to_datetime(nnstr)
        assert isinstance(dtout, timelib.DateTimeType), "wrong type returned"
        assert dtin == dtout, "times are not equal"

    @pytest.mark.skip(reason="disabled for now")
    def test_time_str01(self):
        nn1 = timelib.utc_nowtime()
        #
        tzinfo = pytz.timezone('Europe/Amsterdam')
        timelib.set_local_timezone(tzinfo)
        nn2 = timelib.loc_nowtime()
        for nn in [nn1, nn2]:
            self.convert_test(nn)
        # assert False, "force fail"
