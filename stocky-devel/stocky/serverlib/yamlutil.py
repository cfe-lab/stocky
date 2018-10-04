import typing
import os
import os.path
import yaml
import yaml.scanner
import yaml.parser
import pytz

import serverlib.timelib as timelib


def yamldump(data: typing.Any) -> str:
    """Convert a python data structure to a YAML string.

    Args:
       data: the data structure to convert.
    Returns:
       A string that represents the data in YAML format.
    """
    return yaml.dump(data, Dumper=yaml.CDumper)  # type: ignore


def get_filename(yamlfilename: str, ENV_NAME: str=None) -> str:
    """Determine a complete file name using an optional environment variable.

    If yamlfilename starts with a period ('.') or backslash ('/') or ENV_NAME is None,
    the filename is returned without modification.
    Otherwise, the ENV_NAME environment variable is consulted.
    Its contents are prepended to the filename and this is returned.

    Args:
       yamlfilename: the filename stub to be completed.
       ENV_NAME: the optional name of an environment variable

    Returns:
       A possibly modified file name.

    Raises:
       RuntimeError: if the ENV_NAME is accessed and not defined
    """
    if yamlfilename.startswith('/') or yamlfilename.startswith('.') or ENV_NAME is None:
        return yamlfilename
    dirname = os.environ.get(ENV_NAME, None)
    if dirname is None:
        raise RuntimeError('Environment variable {} is not set'.format(ENV_NAME))
    return os.path.join(dirname, yamlfilename)


def writeyamlfile(data: typing.Any, yamlfilename: str, ENV_NAME: str=None) -> None:
    yamlfilename = get_filename(yamlfilename, ENV_NAME)
    with open(yamlfilename, "w") as fo:
        fo.write(yamldump(data))


def _massage_td(data: typing.Any) -> typing.Any:
    """Convert any timezone unaware datetime instances into timezone aware datetime
    instances in the UTC time zone."""
    if isinstance(data, timelib.DateTimeType):
        return data.astimezone(pytz.utc)
    elif isinstance(data, list):
        return [_massage_td(r) for r in data]
    elif isinstance(data, dict):
        for k, v in data.items():
            data[k] = _massage_td(v)
        return data
    else:
        return data


def readyamlfile(yamlfilename: str, ENV_NAME: str=None) -> typing.Any:
    """Open and read a file containing a data structure in YAML format and return the
    data structure read.

    Args:
       yamlfilename: the name of the file to read
       ENV_NAME: the optional name of an environment variable to use in determining\
       the file location. See :py:func:`get_filename` for how this is done.
    Raises:
       RuntimeError: If any errors occur in reading the file, or if it cannot be found.

    Note:
       Reading and writing datetime instances to a yaml file requires special handling.
       When a timezone-aware datetime is written to a yaml file, the correct timezone
       information is written to the file, e.g. in the form
       of "2018-05-15 18:55:43.916028+02:00", where the +2:00 indicates the UTC+2 time zone.

       However, when reading this back, the time is converted to the same point in time, but
       is returned in UTC time in a timezone *UNAWARE* datetime instance.
       For example, the time in the above example would be 16:44:43.
       In other words, the time read back is implicitly in UTC.
       We convert these datetime records to be timezone aware, that is explicitly in UTC,
       in order to avoid confusion.
    """
    yamlfilename = get_filename(yamlfilename, ENV_NAME)
    try:
        with open(yamlfilename, "r") as fi:
            try:
                data = yaml.load(fi, Loader=yaml.CLoader)  # type: ignore
            except yaml.scanner.ScannerError as e:
                raise RuntimeError("YAML scanning error reading from '{}'\n{}".format(yamlfilename, e))
            except yaml.parser.ParserError as e:
                raise RuntimeError("YAML parse error reading from '{}'\n{}".format(yamlfilename, e))
    except (FileNotFoundError, IsADirectoryError) as e:
        raise RuntimeError("YAML: file not found '{}'".format(yamlfilename))
    return _massage_td(data)
