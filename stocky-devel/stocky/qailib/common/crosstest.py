

class BaseException(Exception):
    def __init__(self, msg):
        self.msg = msg
        js_throw(self)


def js_throw(data: BaseException) -> None:
    """This routine will behave differently, depending on
    whether it is run under Cpython or javascript via transcrypt
    under Cpython: is does nothing.
    under javascript: it throws a javascript exception with the provided instance.
    """
    # NOTE: the pragma is hidden from Cpython in a comment. Transcrypt will nevertheless
    # inject the javascript into the output stream.
    # *** The next line (a python comment) must therefore not be removed.***
    # __pragma__('js', '{}', "throw data;")
    return


def raise_it():
    print("RAISE IT HIGHER")
    raise BaseException("raising the roof")


def assert_it():
    assert False, 'force fail'


class CrossTestCase:
    """A primitive test class that can be run in Cpython as well as compiled
    by Transcrypt.
    Use this class when testing code that:
    a) is ultimately to be run on the client
    b) does not require any database or server functionality to test.
    """
    def __init__(self) -> None:
        # here, we look for any methods whose name start with 'test'
        self._functuplst = ll = []
        for funcname in dir(self):
            if funcname.startswith('test'):
                func = getattr(self, funcname)
                if callable(func):
                    ll.append((funcname, func))

    def setUp(self) -> None:
        print("hello setUp")

    def tearDown(self) -> None:
        print("hello teardown")

    def raises(self, func) -> None:
        """Run provided parameterless function func and
        make sure it raises a BaseException."""
        did_raise = False
        try:
            func()
        except BaseException as b:
            print("caught base exception with msg '{}'".format(b.msg))
            did_raise = True
        except:
            print("In general except")
            did_raise = True
        print("did raise {}".format(did_raise))
        if not did_raise:
            print("func did not raise exception")
            raise BaseException('func did not raise an exception')

    def doassert(self, cond: bool, msg: str) -> None:
        """Raise a Base Exception iff the provided condition is false."""
        if not cond:
            raise BaseException(msg)

    def fail_test(self, msg: str) -> None:
        """Cause a test to fail by raising a BaseException with the provided message."""
        raise BaseException(msg)

    def run(self):
        """Call self.setUp().
        If this is successful, run all tests detected in this class.
        A test is a method whose name begins with 'test'.
        When all tests are run, print test statistics and
        call self.tearDown()
        """
        try:
            self.setUp()
        except:
            print("Setup failed, not running any tests")
            return
        numgood = 0
        fail_lst = []
        for testfuncname, testfunc in self._functuplst:
            print("*** BEGIN {}".format(testfuncname))
            did_pass = True
            try:
                testfunc()
            except:
                did_pass = False
            print("*** END {}".format(testfuncname))
            if did_pass:
                print("** {} SUCCESS\n\n".format(testfuncname))
                numgood += 1
            else:
                print("** {} FAILED\n\n".format(testfuncname))
                fail_lst.append(testfuncname)
        # --
        numran = len(self._functuplst)
        numbad = numran - numgood
        print("ran {} tests: {} failed".format(numran, numbad))
        if len(fail_lst) > 0:
            for fn_name in fail_lst:
                print("failed: {}".format(fn_name))
        self.tearDown()

    # our crosstest has some testing of its own functionality built in.
    def test_except_01(self):
        try:
            raise_it()
        except BaseException as e:
            print("got base exception with msg {}".format(e.msg))

    def test_raises_01(self):
        try:
            self.raises(raise_it)
        except BaseException as e:
            print("GOT RAISES exception '{}'".format(e.msg))

    def test_doassert(self):
        """Check functionality of self.doassert()"""
        self.raises(lambda a: self.doassert(False, 'this is false!'))
        self.doassert(True, 'this should not raise an exception!')

    def test_assert01(self):
        self.raises(assert_it)

    def test_failtest01(self):
        self.raises(lambda a: self.fail_test('this should fail'))
