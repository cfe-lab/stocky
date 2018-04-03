

# module that can start a separate process and issues callbacks to the main program

import gevent
from gevent.subprocess import Popen, PIPE


class SubProcBase:
    def __init__(self, cmdstr: str) -> None:
        """The cmdstr contains the external program name and arguments to run
        in a separate process.
        """
        self.cmdlst = cmdstr.split()
        self._cbfunc = None
        self.do_popen()
        gevent.spawn(self.state_loop)

    def do_popen(self):
        self.p = Popen(self.cmdlst,
                       stdin=PIPE,
                       stdout=PIPE,
                       # stderr=STDOUT,
                       # encoding='utf8',
                       bufsize=1,
                       universal_newlines=True,
                       close_fds=True)

    def state_loop(self):
        """This is the main loop in which we communicate with the subprocess
        and issue callback functions as required.
        We write TO the other program by writing to its stdin.
        self.p.stdin.write("hello\n")
        We read FROM the other program by reading from its stdout.
        line = self.p.stdout.readline()

        This method will typically be of the form:
        while True:
            # write some command to the subprocess...
            self.p.stdin.write("do some work\n")
            # blocking read
            line = self.p.stdout.readline()
            # process the response and issue a callback if required
            some_data = some_process(line)
            if some_data.has_changed() and self._cbfunc is not None:
               self._cbfunc(some_data)
        """
        raise NotImplementedError("state_loop not implemented")

    def reg_CB(self, cbfunc):
        self._cbfunc = cbfunc
