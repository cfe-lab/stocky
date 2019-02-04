"""Provide some low-level utilities for working with timezones
and datetime objects"""

import typing
import datetime as dt
import pytz
import dateutil.parser

DateTimeType = dt.datetime
TimeZoneType = dt.tzinfo


def utc_nowtime() -> DateTimeType:
    """
    Returns:
       The current time as a timezone-aware time in the UTC time zone.
    """
    # NOTE: the following returns a non timezone aware time...not what we want.
    # return dt.datetime.utcnow()
    utc_t = dt.datetime.now(pytz.utc)
    retval = utc_t.astimezone(pytz.utc)
    assert retval.tzinfo is not None, "tzinfo is None!!"
    return retval


_tzinfo: typing.Optional[TimeZoneType] = None


def set_local_timezone(newtzinfo: typing.Union[str, TimeZoneType]) -> None:
    """Set the module's local time zone information.

    Args:
       newtzinfo: either a string denoting a timezone, or a timezone type (datetime.tzinfo)
    """
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


def loc_nowtime_as_string() -> str:
    dt = loc_nowtime()
    return datetime_to_str(dt, True)


def datetime_to_str(dt: DateTimeType, in_local_tz=False) -> str:
    """Convert a date time into a string.
    Args:
       dt: the datetime instance to convert.
       in_local_tz: if True, the string returned will represent the \
         time (dt) in the local timezone (previously set by :meth:`set_local_timezone`)\
         Otherwise, dt is converted as is (i.e. in the timezone provided)
    Returns:
       the datetime information in ISO format.
    Raises:
       RuntimeError: if in_local_tz is True and the local time zone has not been set.
    """
    my_time = dt
    if in_local_tz:
        if _tzinfo is None:
            raise RuntimeError("Must set the local time zone first")
        my_time = dt.astimezone(_tzinfo)
    return my_time.isoformat(sep=' ', timespec='seconds')


def str_to_datetime(s: str) -> DateTimeType:
    """Convert a string into a datetime type.

    Args:
       s: the string to convert. The string must have encoded timezone information.
    Returns:
       The datetime instance.
    Raises:
       RuntimeError: if the conversion fails.
    """
    try:
        retval = dateutil.parser.parse(s)
    except (ValueError, TypeError, OverflowError):
        retval = None
    if retval is None:
        raise RuntimeError("conversion from string to tz failed!")
    return retval
