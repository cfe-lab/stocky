
import pytest
import datetime

import serverlib.LocChangeLib as LocChangeLib


class Test_locchange:

    def setup_method(self) -> None:
        self.lcl = LocChangeLib.LocChangeList()

        CHANGE = LocChangeLib.LocChangeList.changeLocation

        ts = datetime.datetime.now()
        self.change01 = LocChangeLib.LocChange(99, ts, 10, 20, CHANGE)

    def test_add_change01(self):
        """Adding a change should succeed"""
        self.lcl.add_location_change(self.change01)

    def test_add_change02(self):
        """Adding a change twice should fail"""
        self.lcl.add_location_change(self.change01)
        with pytest.raises(RuntimeError):
            self.lcl.add_location_change(self.change01)
