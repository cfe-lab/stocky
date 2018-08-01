
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


def set_local_timezone(newtzinfo: typing.Union[str, TimeZoneType]) -> None:
    if isinstance(newtzinfo, TimeZoneType):
        nnt = newtzinfo
    elif isinstance(newtzinfo, str):
        try:
            nnt = pytz.timezone(newtzinfo)
        except pytz.exceptions.UnknownTimeZoneError:  # type: ignore
            raise RuntimeError("unknown timezone '{}'".format(newtzinfo))
    else:
        raise TypeError("tz must be a tzinfo instance or a string")
    global _tzinfo
    _tzinfo = nnt


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


def datetime_to_str(dt: DateTimeType, in_local_tz=False) -> str:
    """Convert a date time into a string.
    if in_local_tz is True, the string represents the time (dt) in the local
    timezone (previously set by set_local_timezone())
    Otherwise, dt is converted as is (i.e. in the the timezoen provided)
    """
    my_time = dt
    if in_local_tz:
        if _tzinfo is None:
            raise RuntimeError("Must set the local time zone first")
        my_time = dt.astimezone(_tzinfo)
    return my_time.isoformat(sep=' ', timespec='seconds')


def str_to_datetime(s: str) -> DateTimeType:
    """Convert a string into a datetime type.
    The string must have encoded timezone information.
    """
    retval = dateutil.parser.parse(s)
    assert retval.tzinfo is not None, "tzinfo is None!!"
    return retval
