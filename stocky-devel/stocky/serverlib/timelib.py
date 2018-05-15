
import typing
import datetime as dt
import pytz
import dateutil.parser

DateTimeType = dt.datetime
TimeZoneType = dt.tzinfo


def utc_nowtime() -> DateTimeType:
    """Return a timezone aware time of now in the UTZ time zone"""
    # NOTE: the following returns a non timezone aware time...not what we want.
    # return dt.datetime.utcnow()
    utc_t = dt.datetime.now(pytz.utc)
    retval = utc_t.astimezone(pytz.utc)
    assert retval.tzinfo is not None, "tzinfo is None!!"
    return retval


_tzinfo: typing.Optional[TimeZoneType] = None


def set_local_timezone(newtzinfo: TimeZoneType) -> None:
    if not isinstance(newtzinfo, TimeZoneType):
        raise RuntimeError("tz must be a tzinfo instance")
    global _tzinfo
    _tzinfo = newtzinfo


def loc_nowtime() -> DateTimeType:
    """Return a timezone aware time in the local time zone.
    The local timezone must have been previously set.
    """
    if _tzinfo is None:
        raise RuntimeError("set the local timezone with set_local_timezone first")
    utc_t = dt.datetime.now()
    loc_t = utc_t.astimezone(_tzinfo)
    assert loc_t.tzinfo is not None, "tzinfo is None!!"
    return loc_t


def datetime_to_str(dt: DateTimeType) -> str:
    """Convert a date time into a string."""
    return dt.isoformat()


def str_to_datetime(s: str) -> DateTimeType:
    """Convert a string into a datetime type.
    The string must have encoded timezone information.
    """
    retval = dateutil.parser.parse(s)
    assert retval.tzinfo is not None, "tzinfo is None!!"
    return retval
