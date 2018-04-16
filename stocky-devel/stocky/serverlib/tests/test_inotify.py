
import pytest

import serverlib.USBevents as USBevents


class Test_Inotify:
    @pytest.mark.skip(reason="USBlib non-functional under debian-stretch and not used in code")
    def test01(self):
        usb_set = USBevents.get_USB_set()
        assert isinstance(usb_set, set), "set expected!"
        print("USB_SET: {}".format(usb_set))
        # assert False, "Force Fail"

    @pytest.mark.skip(reason="USBlib non-functional under debian-stretch and not used in code")
    def test02(self):
        vend, prod = 0x1050, 0x0407
        usbstate = USBevents.USBState((vend, prod))
        for i in range(60):
            print("state is {}".format(usbstate.isPresent()))
            # time.sleep(1)
        # assert False, "Force Fail"
