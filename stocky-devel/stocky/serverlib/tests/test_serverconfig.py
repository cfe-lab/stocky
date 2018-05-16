
import os
import os.path

import pytest
import py.path

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
        serverconfig.read_server_config(get_testfilename('test02.OK.yaml'))

    def test_L_missing_file(self) -> None:
        "A missing loggingconfig file should raise an error"
        with pytest.raises(RuntimeError):
            serverconfig.read_logging_config(get_testfilename('test0.not_there.yaml'))

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
