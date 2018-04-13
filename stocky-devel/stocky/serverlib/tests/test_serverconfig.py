
import os
import os.path

import pytest

import serverlib.serverconfig as serverconfig


def get_testfilename(fn: str) -> str:
    abspath = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(abspath, 'serverlib-testfiles', fn)


class Test_serverlib:

    def test_missing_file(self):
        "A missing config file should raise an error"
        with pytest.raises(RuntimeError):
            serverconfig.read_server_config(get_testfilename('test0.not_there.yaml'))

    def test_missing_KW(self):
        "A missing keyword should raise a runtime error"
        with pytest.raises(RuntimeError):
            serverconfig.read_server_config(get_testfilename('test01.fail.yaml'))

    def test_should_work(self):
        "Should be able to read a correct file."
        serverconfig.read_server_config(get_testfilename('test02.OK.yaml'))
