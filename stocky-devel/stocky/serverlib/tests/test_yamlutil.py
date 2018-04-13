

import pytest
import serverlib.yamlutil as yamlutil


class Test_yamlutil:

    def test_nofile01(self):
        """Reading a nonexistent file should raise a RuntimeError"""
        with pytest.raises(RuntimeError):
            yamlutil.readyamlfile('bla.goo')


