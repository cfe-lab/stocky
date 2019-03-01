"""Test chemdb, the database abstraction module."""

import pytest

import serverlib.chemdb as chemdb


class TestFuncsChemDB:
    """Test a number of helper functions in the chemdb module,
    These functions do not depend on having a chemdbDB instance.
    """
    def test_sortloclist01(self) -> None:
        """chemdb.sortloclist should preserve list length
        """
        olst = [{'name': r'SPH\West wing'},
                {'name': r'SPH\West wing\dog house'},
                {'name': r'SPH\East Wing'},
                {'name': r'SPH\West wing\cat house'},
                {'name': r'SPH'},
                {'name': r'SPH\East Wing\Aviary'}]

        sortlst = chemdb.sortloclist(olst)
        print("GOOT {}".format(sortlst))
        # assert False, "force fail"
        # NOTE: this is not really checking for correct sorting..
        assert len(olst) == len(sortlst), "wrong list length"

    def test_hash01(self) -> None:
        """chemdb.do_hash must produce the same hash irrespective of the order
        in which dict elements were added to a dict.
        """
        dohash = chemdb.do_hash
        # create two identical dicts in different ways. The hash should be the same.
        adct = dict(a=3, b=2, c=1)
        bdct = {}
        for k, v in sorted(adct.items(), key=lambda a: a[1]):
            bdct[k] = v
        ahash = dohash(adct)
        bhash = dohash(bdct)
        assert ahash == bhash, "hashes are different"

    def test_setnode01(self) -> None:
        """Calling node.setval() twice should raise an exception."""
        n = chemdb.LocNode("blaname")
        assert n.getval() is None, "None expected"
        n.setval('newval99')
        with pytest.raises(RuntimeError):
            n.setval('newval100')
