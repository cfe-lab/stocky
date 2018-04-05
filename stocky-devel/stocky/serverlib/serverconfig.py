

"""
.. module:: serverconfig
    :synopsis: Implement reading of YAML files to configure the stocky server.
"""

# import typing
import math
import serverlib.yamlutil as yamlutil
import pytz
import fuzzywuzzy.process

# configuration files are looked for in the directory defined by this environment variable
CONFIG_DIR_ENV_NAME = 'STOCKY_CONFIG_DIR'

VERSION_FLT = 1.0

known_set = frozenset(['VERSION', 'BT_USB_DEVICE',
                       'BT_READER_ADR', 'RFID_REGION_CODE', 'TIME_ZONE',
                       'RFID_READER_DEVNAME'])


def read_logging_config(yamlfilename: str) -> dict:
    cfg_dct = yamlutil.readyamlfile(yamlfilename, ENV_NAME=CONFIG_DIR_ENV_NAME)
    if not isinstance(cfg_dct, dict):
        raise RuntimeError("config must be a single dict class , but found a {}".format(type(cfg_dct)))
    return cfg_dct


def hexint(instr: str) -> int:
    """Attempt to convert a hex string into an integer.
    Return None iff this fails.
    """
    try:
        i = int(instr, 16)
    except ValueError:
        return None
    return i


def read_server_config(yamlfilename: str) -> dict:
    """Read in a YAML file describing the server configuration.
    Raise a RuntimeError exception iff there is a problem with the file.
    Otherwise return a dictionary of settings.
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

    # check BT_USB_DEVICE: must be a string separated by a colon
    usb_devstr = cfg_dct['BT_USB_DEVICE']
    cols = usb_devstr.split(':')
    is_ok = False
    if len(cols) == 2:
        usb_a = hexint(cols[0])
        usb_b = hexint(cols[1])
        is_ok = usb_a is not None and usb_b is not None
    if not is_ok:
        raise RuntimeError("""Bluetooth USB device name '{}' must be colon separated hex numbers
such as '0a5c:21e8'. Run the 'lsusb' command to see all attached USB devices.""".format(usb_devstr))
    cfg_dct["USB_TUPLE"] = (usb_a, usb_b)

    # check BT_READER_ADR: six colon separated hex numbers.
    bt_adr = cfg_dct['BT_READER_ADR']
    cols = bt_adr.split(':')
    if not(len(cols) == 6 and all([hexint(s) for s in cols])):
        raise RuntimeError("""Bluetooth MAC address '{}' must contain six colon separated numbers.""".format(bt_adr))

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
    except pytz.exceptions.UnknownTimeZoneError:
        print("Error in server config file: unknown timezone '{}'".format(tz_name))
        sugg_names = [n for n, s in fuzzywuzzy.process.extract(tz_name, pytz.all_timezones, limit=10)]
        print("Did you mean any of the following: {} ?".format(", ".join(sugg_names)))
        print("*** To get a list of all possible time zone names, set the time zone variable to '?' ***")
        raise
    cfg_dct['TZINFO'] = tzinfo
    return cfg_dct
