
import os
import os.path

import pytest
import py.path
import unittest.mock as mock
import serverlib.yamlutil as yamlutil
import serverlib.serverconfig as serverconfig


def get_testfilename(fn: str) -> str:
    abspath = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(abspath, 'serverconfig-testfiles', fn)


class Test_serverlib:

    def test_S_missing_file(self) -> None:
        "A missing serverconfig file should raise an error"
        with pytest.raises(RuntimeError):
            serverconfig.read_server_config(get_testfilename('test0.not_there.yaml'))

    def test_S_missing_KW(self) -> None:
        "A missing keyword in a serverconfig file should raise a runtime error"
        with pytest.raises(RuntimeError):
            serverconfig.read_server_config(get_testfilename('test01.fail.yaml'))

    def test_S_should_work(self) -> None:
        "Should be able to read a correct serverconfig file."
        retdct = serverconfig.read_server_config(get_testfilename('test02.OK.yaml'))
        assert isinstance(retdct, dict), "dict expected"
        got_set = set(retdct.keys())
        assert got_set == serverconfig.valid_keys, "unexpected keys"

    def test_L_missing_file(self) -> None:
        "A missing loggingconfig file should raise an error"
        with pytest.raises(RuntimeError):
            serverconfig.read_logging_config(get_testfilename('test0.not_there.yaml'))

    def test_S_wrong_file01(self, tmpdir: py.path.local) -> None:
        "A serverconfig file containing an unknown keyword should raise an error."
        fname = str(tmpdir.join('/bla.yaml'))
        dd = dict(FUNNY=99)
        yamlutil.writeyamlfile(dd, fname)
        with pytest.raises(RuntimeError):
            serverconfig.read_server_config(fname)

    def test_S_wrong_file02(self, tmpdir: py.path.local) -> None:
        "A serverconfig file with missing keywords should raise an error."
        fname = str(tmpdir.join('/bla.yaml'))
        dd = dict(VERSION=99)
        yamlutil.writeyamlfile(dd, fname)
        with pytest.raises(RuntimeError):
            serverconfig.read_server_config(fname)

    def test_S_wrong_file03(self, tmpdir: py.path.local) -> None:
        "A serverconfig file containing a list should raise an error."
        fname = str(tmpdir.join('/bla.yaml'))
        dd = dict(a=1, b=2, gg=77)
        data = [1, 2, 3, 4, dd]
        yamlutil.writeyamlfile(data, fname)
        with pytest.raises(RuntimeError):
            serverconfig.read_server_config(fname)

    def test_S_wrong_values01(self, tmpdir: py.path.local) -> None:
        "A serverconfig file with the wrong values should raise an error."
        fname = str(tmpdir.join('/bla.yaml'))
        dd = serverconfig.read_server_config(get_testfilename('test02.OK.yaml'))
        # remove keys that are not meant to be on file...
        dnew = dict([tt for tt in dd.items() if tt[0] in serverconfig.known_set])
        for k, brokenval in [('VERSION', serverconfig.VERSION_FLT + 0.1),
                             ('RFID_REGION_CODE', 'blaa'),
                             ('TIME_ZONE', '?'),
                             ('TIME_ZONE', 'moon')
                             ]:
            # with mock.patch.dict(dnew, values={k: brokenval}):
            with mock.patch.dict(dnew, {k: brokenval}):
                yamlutil.writeyamlfile(dnew, fname)
                with pytest.raises(RuntimeError):
                    serverconfig.read_server_config(fname)

    def test_L_wrong_file01(self, tmpdir: py.path.local) -> None:
        "A loggingconfig file containing a list should raise an error"
        fname = str(tmpdir.join('/bla.yaml'))
        data = [1, 2, 3, 4]
        yamlutil.writeyamlfile(data, fname)
        with pytest.raises(RuntimeError):
            serverconfig.read_logging_config(fname)

    def test_L_wrong_file02(self, tmpdir: py.path.local) -> None:
        "A loggingconfig file containing a list should raise an error."
        fname = str(tmpdir.join('/bla.yaml'))
        dd = dict(a=1, b=2, gg=77)
        data = [1, 2, 3, 4, dd]
        yamlutil.writeyamlfile(data, fname)
        with pytest.raises(RuntimeError):
            serverconfig.read_logging_config(fname)

    def test_L_wrong_file03(self, tmpdir: py.path.local) -> None:
        "A loggingconfig file containing a single dict should pass."
        fname = str(tmpdir.join('/bla.yaml'))
        data = dict(a=1, b=2, gg=77)
        yamlutil.writeyamlfile(data, fname)
        retval = serverconfig.read_logging_config(fname)
        assert retval == data, "failed to read back data"
