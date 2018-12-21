
import pytest
import datetime

import serverlib.LocChangeLib as LocChangeLib
import serverlib.qai_helper as qai_helper


class Test_locchange:

    def setup_method(self) -> None:
        # self.lcl = LocChangeLib.LocChangeList('bla.sql3')
        self.lcl = LocChangeLib.LocChangeList()

        CHANGE_OP = LocChangeLib.LocChange.changeLocation
        CONFIRM_OP = LocChangeLib.LocChange.confirmLocation
        MISSING_OP = LocChangeLib.LocChange.markMissing

        # a and b are identical, c is different, but has the same itemid.
        ts = datetime.datetime.now()
        self.change01a = LocChangeLib.LocChange(99, ts, 10, 20, CHANGE_OP)
        self.change01b = LocChangeLib.LocChange(99, ts, 10, 20, CHANGE_OP)
        self.change01c = LocChangeLib.LocChange(99, ts, 10, 30, CHANGE_OP)
        # change02 has a different itemid
        self.change02 = LocChangeLib.LocChange(100, ts, 99, 98, CHANGE_OP)

        # illegal opcode
        self.faultychange01 = LocChangeLib.LocChange(100, ts, 99, 98, 'Z')

        self.confirm01 = LocChangeLib.LocChange(120, ts, 99, None, CONFIRM_OP)

        self.missing01 = LocChangeLib.LocChange(125, ts, 99, None, MISSING_OP)

        self.valid_changes = [self.change01a, self.change02,
                              self.confirm01, self.missing01]

    def test_eq01(self):
        """The __eq__ method of LocChange must work with LocChange instances"""
        # self.assertEqual(self.change01, self.change02)
        assert self.change01a == self.change01b
        assert not self.change01a == self.change02

    def test_eq02(self):
        """The __eq__ method should hanlde comparisons gracefully"""
        for val in ["now", 1.0, 99]:
            res = self.change01a == "now"
            # print("RES is {}".format(res))
            assert not res, "expected False"
        # assert False, "force fail"

    def test_asdict01(self):
        """Converting a LocChange to and from dict should produce an equivalent change record."""
        trec = self.confirm01
        tdct = trec.as_dict()
        assert isinstance(tdct, dict), "dict expected"
        newrec = LocChangeLib.LocChange.from_dict(tdct)
        assert trec == newrec, "newrec is not same!"

    def test_add_change01(self):
        """Adding a new change should succeed. Reading it back should produce the same value."""
        change01 = self.change01a
        self.lcl.add_location_change(change01)
        retval = self.lcl.get_location_change(change01.itemid)
        print("change: {}".format(change01))
        print("retval: {}".format(retval))
        assert retval == change01, "added item not the same"

    def test_valid_opcode(self):
        """The LocChange.has_valid_opcode() must work."""
        assert self.change01a.has_valid_opcode(), "opcode test failed"
        assert not self.faultychange01.has_valid_opcode(), "opcode test failed"

    def test_add_faulty01(self):
        """Adding a change with a wrong opcode should raise a RuntimeError"""
        with pytest.raises(RuntimeError):
            self.lcl.add_location_change(self.faultychange01)

    def test_get_missing01(self):
        """Retreiving an non-existing locchange should return None"""
        retval = self.lcl.get_location_change(self.change01a.itemid)
        assert retval is None, "expected a retval of None"

    def test_mod_change02(self):
        """Modifying an existing change should result in a change."""
        # first, add change01a
        self.lcl.add_location_change(self.change01a)
        self.lcl.add_location_change(self.change02)
        retval = self.lcl.get_location_change(self.change01a.itemid)
        assert retval == self.change01a, "added item not the same"
        # accessing change02 should not be affected
        assert self.lcl.get_location_change(self.change02.itemid) == self.change02
        # now add first1c
        self.lcl.add_location_change(self.change01c)
        retval = self.lcl.get_location_change(self.change01a.itemid)
        assert retval == self.change01c, "added item not the same"
        # accessing change02 should not be affected
        assert self.lcl.get_location_change(self.change02.itemid) == self.change02

    def test_add_confirm01(self):
        """Adding a new location confirmation should succeed.
        Reading it back should produce the same value."""
        change01 = self.confirm01
        self.lcl.add_location_change(change01)
        retval = self.lcl.get_location_change(change01.itemid)
        print("change: {}".format(change01))
        print("retval: {}".format(retval))
        assert retval == change01, "added item not the same"

    def test_add_missing01(self):
        """Adding a missing change log should succeed.
        Reading it back should produce the same value."""
        change01 = self.missing01
        self.lcl.add_location_change(change01)
        retval = self.lcl.get_location_change(change01.itemid)
        print("change: {}".format(change01))
        print("retval: {}".format(retval))
        assert retval == change01, "added item not the same"

    def test_get_all01(self):
        """Retrieving all changelogs should succeed."""
        for ch in self.valid_changes:
            self.lcl.add_location_change(ch)
        inp_id_set = set([r.itemid for r in self.valid_changes])
        retlst = self.lcl.get_all_location_changes()
        assert isinstance(retlst, list), "list type expected"
        if len(self.valid_changes) != len(retlst):
            raise RuntimeError('unexpected number of items {} vs {}'.format(len(self.valid_changes),
                                                                            len(retlst)))
        for retrec in retlst:
            assert isinstance(retrec, LocChangeLib.LocChange), "LocChange instance expected"
        out_id_set = set([r.itemid for r in retlst])
        assert inp_id_set == out_id_set, "unexpected ID set"

    def test_get_all02(self):
        """Retrieving all changelogs from an empty database should succeed."""
        retlst = self.lcl.get_all_location_changes()
        assert isinstance(retlst, list), "list type expected"
        assert len(retlst) == 0, "expected an empty list"

    def test_get_all03(self):
        """Retrieving all changelogs should succeed."""
        for ch in self.valid_changes:
            self.lcl.add_location_change(ch)
        inp_id_set = set([r.itemid for r in self.valid_changes])
        retlst = self.lcl.get_all_location_changes()
        dctlst = [r.as_dict() for r in retlst]
        js_string = qai_helper.tojson(dctlst)
        ret2lst = qai_helper.fromjson(js_string)
        assert isinstance(ret2lst, list), "list type expected"
        if len(self.valid_changes) != len(retlst):
            raise RuntimeError('unexpected number of items {} vs {}'.format(len(self.valid_changes),
                                                                            len(retlst)))
        for retrec in retlst:
            assert isinstance(retrec, LocChangeLib.LocChange), "LocChange instance expected"
        out_id_set = set([r.itemid for r in retlst])
        assert inp_id_set == out_id_set, "unexpected ID set"
