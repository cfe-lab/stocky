

import qailib.common.formbase as formbase


class testmixin:
    """A class that provides some tests of formbase that should be tested
    both under Cpython and compiled by Transcrypt."""

    def test_portable_str_to_int01(self):
        """Test the string to int conversion routine portable_str_to_int() """
        str_lst = [('100', 100), ('abc', None), ('100.3', None), ('-1', -1),
                   ('', None), ('  ', None),
                   ('100bla', None), ('bla100', None)]
        do_fail = False
        for strdat, exp_res in str_lst:
            res = formbase.portable_str_to_int(strdat)
            if res != exp_res:
                print("unexpected result '{}' for input '{}' Expected '{}'".format(res, strdat, exp_res))
                do_fail = True
            if exp_res is not None:
                if not isinstance(res, int):
                    print("   integer expected, but got something else!")
                    do_fail = True
        # --
        assert not do_fail, "stopping"

    def do_testmixin(self, lverb: bool, mixin: formbase.BaseValidateMixin,
                     cnv_lst, xtra_lst) -> None:
        """Helper function to test a givin mixin with test data"""
        # test string to int conversion
        do_fail = False
        for instr, exp_val in cnv_lst:
            retval = mixin.convert_to_python(instr)
            if retval != exp_val:
                print("convert: unexpected result for value '{}': expected {}, but got {}".format(instr,
                                                                                                  exp_val,
                                                                                                  retval))
                do_fail = True
        assert not do_fail, "stopping"

        # test extra validation (e.g. ranges)
        for inval, exp_bool in xtra_lst:
            retval = mixin.extra_validate_isok(inval)
            assert isinstance(retval, bool), "expected bool"
            if retval != exp_bool:
                print("extra_validate: unexpected result for value '{}': expected {}, but got {}".format(inval,
                                                                                                         exp_bool,
                                                                                                         retval))
                do_fail = True
            assert not do_fail, "stopping"
        # test get_clean data...
        # first convert our cnv and range test data
        big_lst = [t for t in cnv_lst]
        for num, isok in xtra_lst:
            big_lst.append(("{}".format(num), num if isok else None))
        for instr, exp_val in big_lst:
            retval = mixin.get_clean_data(instr)
            if retval != exp_val:
                print("clean_data: unexpected result for value '{}': expected {}, but got {}".format(instr,
                                                                                                     exp_val,
                                                                                                     retval))
                do_fail = True
            assert not do_fail, "stopping"

    def test_IntValidateMixin01(self, lverb=True):
        """Test the IntValidateMixin01."""
        minval, maxval = -100, 200
        iv = formbase.IntValidateMixin(dict(min=minval, max=maxval))
        # test string to int conversion
        str_lst = [('100', 100), ('abc', None), ('100.3', None),
                   ('-1', -1), (' 100', 100), ('100  ', 100), ('+20', 20),
                   ('', None), ('  ', None)]
        # test extra validation (ranges)
        range_lst = [(minval, True), (maxval, True),
                     (minval+1, True), (maxval-1, True),
                     (maxval+1, False), (minval-1, False)]
        self.do_testmixin(lverb, iv, str_lst, range_lst)

    def test_BoolValidateMixin01(self, lverb=True):
        """Test the BoolValidateMixin01."""
        iv = formbase.BoolValidateMixin()
        # test string to bool conversion
        str_lst = [('True', True),
                   ('abc', None),
                   ('100.3', None),
                   ('100', None),
                   (' True', True),
                   (' False  ', False),
                   ('', None), ('  ', None)]
        # test extra validation (ranges)
        range_lst = []
        self.do_testmixin(lverb, iv, str_lst, range_lst)

    def test_EmailValidateMixin01(self, lverb=True):
        ev = formbase.EmailValidateMixin()
        str_lst = [(' goo@bla.com  ', 'goo@bla.com'), ('abc@bla.com', 'abc@bla.com')]
        val_lst = [('bla@funny.com', True), ("some@body@bla.com", False),
                   ('jump@', False), ('@bla.com', False), ('my.name@bla.com', True),
                   ('.bla@hello.com', False), ('bla@hello.', False),
                   ('   ', False), ("bla@some.where.com", True),
                   (' jump#@goo', False)]
        self.do_testmixin(lverb, ev, str_lst, val_lst)
