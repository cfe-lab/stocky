
import typing
import pytest
import py.path
import unittest.mock as mock
import os
import os.path

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

    def test_get_filename01(self) -> None:
        """
        Test yamlutil.get_filename: a nonexistent environment variable should raise an exception;
        an existing environment variable should work as expected.
        """
        fname = 'hello.dolly'
        envname = 'SCOENV'
        # a: nonexistent env var should raise an exception
        with pytest.raises(RuntimeError):
            yamlutil.get_filename(fname, envname)
        # b: existing env var should work
        envval = 'bladir'
        exp_str = os.path.join(envval, fname)
        with mock.patch.dict(os.environ, {envname: envval}):
            got_str = yamlutil.get_filename(fname, envname)
            print('retstr {}'.format(got_str))
            assert exp_str == got_str, 'unexpectd str'
        # assert False, 'force fail'

    def test_readscanner01(self, tmpdir: py.path.local) -> None:
        """A YAML scanning error should raise an exception."""
        locfname = str(tmpdir.join('/bla.yaml'))
        with open(locfname, "w") as fo:
            fo.write(r"!?\}")
        with pytest.raises(RuntimeError):
            yamlutil.readyamlfile(locfname)
        # print("got '{}'".format(d))
        # assert False, "force fail"

    def test_readparse01(self, tmpdir: py.path.local) -> None:
        """A YAML parsing error should raise an exception."""
        locfname = str(tmpdir.join('/bla.yaml'))
        with open(locfname, "w") as fo:
            fo.write("[1, 2, }")
        with pytest.raises(RuntimeError):
            yamlutil.readyamlfile(locfname)
        # print("got '{}'".format(d))
        # assert False, "force fail"

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
