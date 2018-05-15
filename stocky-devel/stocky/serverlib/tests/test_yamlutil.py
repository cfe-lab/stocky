
import typing
import pytest
import py.path
import pytz

import serverlib.yamlutil as yamlutil
import serverlib.timelib as timelib


class Test_yamlutil:

    def setup_method(self) -> None:
        self.utctime = timelib.utc_nowtime()
        ams = pytz.timezone('Europe/Amsterdam')
        timelib.set_local_timezone(ams)
        self.loctime = timelib.loc_nowtime()

    def test_nofile01(self) -> None:
        """Reading a nonexistent file should raise a RuntimeError"""
        with pytest.raises(RuntimeError):
            yamlutil.readyamlfile('bla.goo')

    def check_dump(self, fname: str, data: typing.Any, lverb: bool) -> None:
        """Dump some data, read it back and compare to the original"""
        yamlutil.writeyamlfile(data, fname)
        if lverb:
            with open(fname, "r") as fi:
                print("the file is '{}'".format(fi.read()))
        # now read it back and compare
        newnn = yamlutil.readyamlfile(fname)
        print("new time is {}".format(newnn))
        assert data == newnn, "saved and restored data is not equal!"

    def test_time01(self, tmpdir: py.path.local) -> None:
        """Dumping a UTC time with tzinfo and reading it back should produce the same time"""
        locfname = str(tmpdir.join('/bla.yaml'))
        self.check_dump(locfname, self.utctime, False)

    def test_time02(self, tmpdir: py.path.local) -> None:
        """Dumping a local time with tzinfo and reading it back should produce the same time"""
        locfname = str(tmpdir.join('/bla.yaml'))
        self.check_dump(locfname, self.loctime, False)
        # assert False, "force fail"

    def test_dumpdata(self, tmpdir: py.path.local) -> None:
        """Dumping some data structures and reading them back should succeed."""
        locfname = str(tmpdir.join('/bla.yaml'))
        d1 = dict(a=1, b=3, c=99, dd=self.loctime)
        l1 = ['a', 99.0, self.utctime, 22, 'bla']
        for testdata in [d1, l1]:
            self.check_dump(locfname, testdata, False)
