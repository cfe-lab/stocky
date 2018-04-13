
import typing
import os
import os.path
import yaml


def yamldump(data: typing.Any) -> str:
    """Return a string that represents the data
    in YAML format."""
    return yaml.dump(data, Dumper=yaml.CDumper)  # type: ignore


def _get_filename(yamlfilename: str, ENV_NAME: str) -> str:
    if yamlfilename.startswith('/'):
        return yamlfilename
    if not yamlfilename.startswith('.') and ENV_NAME is not None:
        dirname = os.environ.get(ENV_NAME, None)
        if dirname is not None:
            yamlfilename = os.path.join(dirname, yamlfilename)
    return yamlfilename


def writeyamlfile(data: typing.Any, yamlfilename: str, ENV_NAME: str=None) -> None:
    yamlfilename = _get_filename(yamlfilename, ENV_NAME)
    with open(yamlfilename, "w") as fo:
        fo.write(yamldump(data))


def readyamlfile(yamlfilename: str, ENV_NAME: str=None) -> typing.Any:
    """Open and read a file containing a data structure in YAML format and return the
    data structure read.

    If the yamlfilename does not start witha period and ENV_NAME is not None, then the
    contents of an environment variable called ENV_NAME is accessed.
    If this is successful, the file name is looked for in the directory specified by the
    environment variable ENV_NAME.
    This function will raise a RuntimeError if there are any problems.
    """
    yamlfilename = _get_filename(yamlfilename, ENV_NAME)
    try:
        with open(yamlfilename, "r") as fi:
            try:
                data = yaml.load(fi, Loader=yaml.CLoader)  # type: ignore
            except yaml.scanner.ScannerError as e:
                raise RuntimeError("YAML scanning error reading from '{}'\n{}".format(yamlfilename, e))
            except yaml.parser.ParserError as e:
                raise RuntimeError("YAML parse error reading from '{}'\n{}".format(yamlfilename, e))
    except FileNotFoundError as e:
        raise RuntimeError("YAML: file not found '{}'".format(yamlfilename))
    return data
