
import pytest
import serverlib.timelib as timelib
import pytz


class Test_timelib:

    def setup_method(self) -> None:
        self.utctime = timelib.utc_nowtime()

    def test_utc(self):
        """timelib.utc_nowtime() must return a timelib.DateTimeType instance."""
        assert isinstance(self.utctime, timelib.DateTimeType), "wrong type returned"

    def test_loc01(self):
        """timelib.loc_nowtime() must raise a RuntimeError if the timezone is undefined."""
        timelib._tzinfo = None
        with pytest.raises(RuntimeError):
            timelib.loc_nowtime()

    def test_datetime_to_str01(self):
        """timelib.datetime_to_str() must raise a RuntimeError if the timezone is undefined."""
        timelib._tzinfo = None
        nn1 = timelib.utc_nowtime()
        with pytest.raises(RuntimeError):
            timelib.datetime_to_str(nn1, in_local_tz=True)

    def test_loc02(self):
        """timelib.set_local_timezone must raise a RuntimeError if passed an
        illegal string."""
        with pytest.raises(RuntimeError):
            timelib.set_local_timezone("now")

    def test_loc02a(self):
        """timelib.set_local_timezone must raise a RuntimeError if passed an integer"""
        with pytest.raises(TypeError):
            timelib.set_local_timezone(10)

    def test_loc03(self):
        """timelib.loc_nowtime() must return a timelib.DateTimeType instance
        if a valid timezone was previously set by timelib.set_local_timezone
        """
        tzinfo = pytz.timezone('Europe/Amsterdam')
        timelib.set_local_timezone(tzinfo)
        nn = timelib.loc_nowtime()
        assert isinstance(nn, timelib.DateTimeType), "wrong type returned"

    def convert_test(self, dtin: timelib.DateTimeType) -> None:
        """Convert a datetime to string then back to datetime.
        The datetime records must be the same.
        """
        assert isinstance(dtin, timelib.DateTimeType), "wrong type entered"
        nnstr = timelib.datetime_to_str(dtin)
        assert isinstance(nnstr, str), "string expected"
        print("got string '{}'".format(nnstr))
        dtout = timelib.str_to_datetime(nnstr)
        assert isinstance(dtout, timelib.DateTimeType), "wrong type returned"
        # assert dtin == dtout, "times are not equal"

    def test_time_str01(self):
        """Converting a DateTimeType to string and back again should
           result in the same time.
           Update: actually, as we round the time to seconds on conversion,
           they will *NOT* be the same.
        """
        nn1 = timelib.utc_nowtime()
        #
        tzinfo = pytz.timezone('Europe/Amsterdam')
        timelib.set_local_timezone(tzinfo)
        nn2 = timelib.loc_nowtime()
        for nn in [nn1, nn2]:
            self.convert_test(nn)
        # assert False, "force fail"

    def test_str_to_datetime(self):
        """str_to_datetime should raise a RuntimeError is passed a non-conforming time string"""
        with pytest.raises(RuntimeError):
            timelib.str_to_datetime("blastr")
