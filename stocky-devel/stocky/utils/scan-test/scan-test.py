# This is a version of the stocky main program used to test different forms of RFID scanning
# IT does not have a web interface, but just scans in an infinite loop
# The stocky main program using Flask socket
# See the runserver.sh script in this directory for how to launch the program.

import typing
# from geventwebsocket import websocket
import serverlib.serverconfig as serverconfig
import serverlib.commlink as commlink
import serverlib.stockyserver as stockyserver
import serverlib.Taskmeister as Taskmeister

import logging.config
import flask
from flask_sockets import Sockets


def get_logger_name(mylogger) -> str:
    ld = logging.Logger.manager.loggerDict
    # print("loggernames {}".format(ld.keys()))
    for k, v in ld.items():
        if v == mylogger:
            return k
    return 'not found'


def test_logging(l):
    """Ensure that the logging configuration is what we think it is.
    This routine is disabled during normal operations.
    """
    print("app logger is called '{}'".format(get_logger_name(app.logger)))
    print("EFF LEVEL {}".format(l.getEffectiveLevel()))
    print("LL is {}".format(l))
    l.debug("debug level")
    l.info("info level")
    l.warn("warn level")
    l.error("error level")
    l.critical("critical level")


logging.config.dictConfig(serverconfig.read_logging_config('logging.yaml'))
the_main = None
app = flask.Flask(__name__.split('.')[0])
test_logging(app.logger)
socky = Sockets(app)
# app.logger.debug('hoity toity')


def gen_arglst() -> typing.List[str]:
    modtt = ('io', )
    retlst = []
    retlst.append('.iv -x')
    numvar = len(modtt)
    numcase = 2 ** numvar
    oodct = {True: 'on', False: 'off'}
    cmdstr1 = '.iv -al off -e on -r on -ie on -o 29'
    for icase in range(numcase):
        mask = 1
        cmdstropt = ''
        for bit in range(numvar):
            cmdstropt += " -{} {} ".format(modtt[bit], oodct[(mask & icase) != 0])
            mask *= 2
        cmdstr = cmdstr1 + cmdstropt + '-ql all -fi on'
        retlst.append(cmdstr)
    retlst.append('')
    retlst.append('.iv -p')
    assert len(retlst) == numcase+3, "list is wrong length"
    print("\n".join(retlst))
    return retlst


def init_app(cfgname: str):
    """This routine is used a helper in order to launch the serverclass with the
    name of a configuration file, e.g. in a launching shell script, such as runserver.sh,
    we would write something like:
    gunicorn -k flask_sockets.worker "stocky:init_app('scoconfig.yaml')" --bind 0.0.0.0:5000
    """
    global the_main
    the_main = stockyserver.serverclass(app, commlink.SerialCommLink, cfgname)
    # logging.config.dictConfig(serverconfig.read_logging_config('logging.yaml'))

    arg_lst = gen_arglst()
    gencmd = Taskmeister.CommandListGenerator(the_main.msgQ,
                                              the_main.logger,
                                              1,
                                              'listgen', arg_lst)
    gencmd.set_active(True)
    the_main.timerTM.set_active(True)
    the_main.mainloop(None)
    return app


if __name__ == "__main__":
    print("Sorry Dave, stocky.py main program will not run....")
    print("Start the stocky server using the runserver.sh script")
    print("""Or something like:
'gunicorn -k flask_sockets.worker "stocky:init_app('serverconfig.yaml')" --bind 0.0.0.0:5000'""")
