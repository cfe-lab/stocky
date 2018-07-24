
# client side
import qailib.common.base as base
import qailib.common.serversocketbase as serversocketbase
import qailib.common.crosstest as crosstest

from webclient.commonmsg import CommonMSG


class T1:
    A = 'Astring'
    B = 'Bstring'
    C = 'Cstring'

    @classmethod
    def do_init(cls) -> None:
        cls.L = [cls.A, cls.B, cls.C]


T1.do_init()


class testserver_socket(serversocketbase.base_server_socket):
    """Define a server_socket class for testing under CPython.
    The idea is that send passes a request to the server.
    The server response is passed to all listeners.
    """
    def __init__(self, idstr: str, username: str) -> None:
        super().__init__(idstr)
        self._username = username

    def send(self, d_in) -> None:
        """Convert the data structure to JSON before sending it
        to the server."""
        # print("send {}".format(d_in))
        # for more rigorous testing, we also convert to json and back again
        # as this also ensures that all data structures are serialisable and
        # can be sent over the wire
        # new_d_in = consumers.fromjson(consumers.tojson(d_in))
        # res_dct = consumers.handle_msgdct(self._username, new_d_in)
        # lets pretend the server has returned right away --> pass the response back
        res_dct = {'ok': False}
        self.sndMsg(base.MSGD_SERVER_MSG, res_dct)


# class Tester(crosstest.CrossTestCase, formbasetest.testmixin):
class Tester(crosstest.CrossTestCase):
    def __init__(self) -> None:
        super().__init__()
        self.run()

    def test_classvar01(self) -> None:
        # c = T1()
        print("A is {}".format(T1.A))
        print("L is {}".format(T1.L))

    def test_commonmsg01(self) -> None:
        c = CommonMSG(CommonMSG.MSG_SV_RAND_NUM, 10)
        assert c.msg == CommonMSG.MSG_SV_RAND_NUM, "wrong msg"
        assert c.data == 10, "wrong data"
        ll = CommonMSG.valid_msg_lst
        assert ll, "msg_lst expected"
        print("lst is {}".format(ll))
        #
        # ll = CommonMSG.bla
        # print("lst is {}".format(ll))
        # assert ll, "ll is empty"
        dd = CommonMSG.valid_msg_dct
        assert dd, "msg_dct expected"
        print("dct is {}".format(dd))

    def DO_NOT_test_sets_01(self):
        """Have been having problems testing for sets of strings in javascript -python.
        See the test report below.
        """
        print("test_sets_01!")
        big_set = serversocketbase.allowed_qmode_set
        # big_set = serversocketbase.mutation_qmode_set
        print('big set is : {}'.format(big_set))
        for fn in ['READ']:
            print(" setty: '{}' is in: {}".format(fn, fn in big_set))
        alst = ['one', 'two', 'three']
        aset = set(alst)
        blst = ['three', 'four']
        # NOTE: alst + blst WILL not produce the required result in transcrypt
        # because of javascript (no operator overloading)
        c1set = set(alst + blst)
        clst = alst + blst
        alst.extend(blst)

        c2set = set(clst)
        print("  one in aset: {}".format('one' in aset))
        print("aset : {}".format(aset))
        print("clst : {}".format(clst))
        print("c1set: {}".format(c1set))
        print("c2set: {}".format(c2set))
        print("c3lst: {}".format(alst))
        cset = set(alst)
        print("c3set: {}".format(cset))

    def DO_NOT_test_report01(self):
        """File a transcrypt error.
        UPDATE: This was done, but the difference in behaviour between javascript and
        python is a 'feature'.
        We cannot use 'alst + blst ' when using transcrypt.
        """
        print("test_report_01!")
        alst = ['one', 'two', 'three']
        blst = ['three', 'four']
        clst = alst + blst
        # clst is faulty
        dlst = ['one', 'two', 'three']
        dlst += blst
        # dlst is faulty
        elst = ['one', 'two', 'three']
        # elst is correct
        elst.extend(blst)
        print("alst : {}".format(alst))
        print("blst : {}".format(blst))
        print("clst : {}".format(clst))
        print("dlst : {}".format(dlst))
        print("elst : {}".format(elst))

    def DO_NOT_test_fail_01(self):
        """This demonstrates that javascript does not raise a key error.
        There is nothing we do about this."""
        def fail_01():
            ad = {'a': 1.0}
            c = ad['noway']
            print("this should have failed, but c is {}".format(c))
        self.raises(fail_01)

    def dictyfunc(self):
        print("dictyfunc")
        a = dict(a=1, b=2, c=3)
        for k, v in a.items():
            print(k)

    def listyfunc(self):
        print("listyfunc")
        ll = [1, 2, 3, 4, 5]
        for x in ll:
            print(x)


# the main program
print('hello from main')
t = Tester()
# phantom.exit()
