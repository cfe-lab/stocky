#!/usr/bin/env python3

# A module to be imported by stocky main server program
# it starts a separate process that checks for USB state

# import subprocess

import serverlib.SubProc as SubProc
import gevent


PROG = "/stockysrc/serverlib/USBevents.py"


class USBProc(SubProc.SubProcBase):
    def __init__(self, prod_tup):
        self.onstate = False
        self.n = 0
        cmd = "{} -m {} -p {} ".format(PROG, prod_tup[0], prod_tup[1])
        super().__init__(cmd)

    def state_loop(self):
        lverb = False
        if lverb:
            print("started subprocess..")
            print("writing...")
        self.p.stdin.write("dddd\n")
        while True:
            if lverb:
                print("check {}".format(self.n))
            self.n += 1
            if lverb:
                print("reading...")
            line = self.p.stdout.readline()
            if lverb:
                print("GOOOT {}".format(line))
            if line:
                sl = line.split(":")
                if len(sl) == 3:
                    newstate = eval(sl[2])
                    self._change_state(newstate)
                    if lverb:
                        print("STATE={}".format(self.onstate))

    def _change_state(self, newstate):
        if self.onstate != newstate:
            self.onstate = newstate
            if self._cbfunc is not None:
                self._cbfunc(newstate)

    def get_state(self) -> bool:
        return self.onstate


def dotest():
    b = USBProc((4176, 1031))
    # b.state_loop()
    for i in range(100):
        st = b.get_state()
        print("state is {}".format(st))
        gevent.sleep(1.0)


if __name__ == "__main__":
    dotest()
