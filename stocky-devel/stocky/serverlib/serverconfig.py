"""
Implement the reading of YAML files to configure the stocky server.
"""

import math
import serverlib.yamlutil as yamlutil
import pytz
import pytz.exceptions
import fuzzywuzzy.process

# configuration files are looked for in the directory defined by this environment variable
CONFIG_DIR_ENV_NAME = 'STOCKY_CONFIG_DIR'

# state files (such as the QAI stock list and log files) are looked for in the
# directory defined by this environment variable
STATE_DIR_ENV_NAME = 'STOCKY_STATE_DIR'


VERSION_FLT = 1.0

# these are the kyes that must be on file
known_set = frozenset(['VERSION', 'RFID_REGION_CODE', 'TIME_ZONE',
                       'RFID_READER_DEVNAME', 'QAI_URL',
                       'LOCAL_STOCK_DB_FILE'])

# these are the keys on file PLUS the ones added after reading the yaml file
valid_keys = known_set | frozenset(['TZINFO'])


def read_logging_config(yamlfilename: str) -> dict:
    """Read in a YAML logging configuration file.

    Args:
       yamlfilename: the file name to read
    Returns:
       The dict contained in the YAML file.
    Raises:
       RuntimeError: If the config file contains anything but a single dictionary.
    """
    cfg_dct = yamlutil.readyamlfile(yamlfilename, ENV_NAME=CONFIG_DIR_ENV_NAME)
    if not isinstance(cfg_dct, dict):
        raise RuntimeError("logging config must be a single dict class , but found a {}".format(type(cfg_dct)))
    return cfg_dct


def read_server_config(yamlfilename: str) -> dict:
    """Read in a YAML file describing the server configuration.

    Args:
       yamlfilename: The name of the file to read.
    Returns:
       A dict containing the server configuration.
    Raises:
       RuntimeError: iff there is a problem with the file. A number of checks are performed.
    """
    cfg_dct = yamlutil.readyamlfile(yamlfilename, ENV_NAME=CONFIG_DIR_ENV_NAME)
    if not isinstance(cfg_dct, dict):
        raise RuntimeError("config must be a single dict class , but found a {}".format(type(cfg_dct)))
    have_set = set(cfg_dct.keys())
    unknown_set = have_set - known_set
    if unknown_set:
        raise RuntimeError("Unknown settings '{}'; known settings are '{}'".format(unknown_set,
                                                                                   ", ".join([n for n in known_set])))
    missing_set = known_set - have_set
    if missing_set:
        raise RuntimeError("Missing settings '{}'".format(", ".join([n for n in missing_set])))

    # check the version string
    ver_flt = cfg_dct['VERSION']
    if math.fabs(ver_flt - VERSION_FLT) > 0.001:
        raise RuntimeError("Required VERSION = {}, but got {}".format(VERSION_FLT, ver_flt))

    # check RFID_REGION_CODE: just check length.
    reg_code = cfg_dct['RFID_REGION_CODE']
    if len(reg_code) != 2:
        raise RuntimeError("""RFID region code '{}' must be of length 2""".format(reg_code))

    # make sure we know the time zone...
    tz_name = cfg_dct['TIME_ZONE']
    if tz_name == '?':
        # help function -- print all time_zone names and exit.
        print("Time zone helper (TIME_ZONE in config file). All timezones are:")
        print("\n".join(pytz.all_timezones))
        raise RuntimeError("TIME_ZONE helper: exiting")
    try:
        tzinfo = pytz.timezone(tz_name)
    except pytz.exceptions.UnknownTimeZoneError:  # type: ignore
        print("Error in server config file: unknown timezone '{}'".format(tz_name))
        sugg_names = [n for n, s in fuzzywuzzy.process.extract(tz_name, pytz.all_timezones, limit=10)]
        print("Did you mean any of the following: {} ?".format(", ".join(sugg_names)))
        print("*** To get a list of all possible time zone names, set the time zone variable to '?' ***")
        raise RuntimeError('Unknown timezone')
    cfg_dct['TZINFO'] = tzinfo
    return cfg_dct
