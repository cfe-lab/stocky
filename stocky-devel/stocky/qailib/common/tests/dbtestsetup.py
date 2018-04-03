

# provide some mixin classes that help is setting up some basic database entries for testing

import collections

import django.contrib.auth.models
import webqai.models as models
import webqai.consumers as consumers

import qailib.common.base as base
from qailib.common.serversocketbase import base_server_socket
import qailib.common.dataelements as dataelements
import qailib.common.serversocketbase as serversocketbase


class SimpleDBSetupMixin:
    def setUpDB(self):
        """Put some data into the test database"""
        # some users.
        self.jane_username = 'JaneDoe'
        johntup = ('JohnnyDoe', 'Johnny', 'Doe', 'johndoe@hotmail.com', True, 'Zanzibar')
        janetup = (self.jane_username, 'Jane', 'Doe', 'janedoe@hotmail.com', False, 'Lac St Jean')
        bobotup = ('BoboDoe', 'Bobo', 'Doe', 'bobodoe@hotmail.com', True, 'Pankow')
        self._user_list = ulist = [johntup, janetup, bobotup]
        for un, fn, ln, em, is_log_in, loc in ulist:
            uu = django.contrib.auth.models.User.objects.create(username=un,
                                                                first_name=fn,
                                                                last_name=ln,
                                                                email=em)
            models.UserProfile.objects.filter(pk=uu.pk).update(is_logged_in=is_log_in,
                                                               location=loc)
        self.john_id = 1
        self.jane_id = 2
        self.bobo_id = 3

        self.john_idstr = '1'
        self.jane_idstr = '2'
        self.bobo_idstr = '3'

        self.usermodelname = 'User'
        # some UserTags
        tag_inp_lst = [('Clinical', "lab members involved in clinical work"),
                       ('MassSpec', 'lab members who use the Mas Spec'),
                       ('EveryOne', 'all lab members')]
        tag_lst = [models.UserTag.create(nm, desc) for nm, desc in tag_inp_lst]
        clin_ut = tag_lst[0]
        every_ut = tag_lst[2]

        clin_manager = models.UserRoleTag.MANAGER(clin_ut)
        every_user = models.UserRoleTag.USER(every_ut)
        # add users to various groups and roles
        john_up = models.UserProfile.objects.get(pk=self.john_id)
        john_up.add_allowed_roletag(every_user)

        jane_up = models.UserProfile.objects.get(pk=self.jane_id)
        jane_up.add_allowed_roletag(every_user)
        jane_up.add_allowed_roletag(clin_manager)

        # only clinical managers can create and delete (other people's) User records
        for crudop in [models.TableAccess.TA_CRUD_CREATE,
                       models.TableAccess.TA_CRUD_DELETE]:
            models.TableAccess.create(self.usermodelname,
                                      crudop,
                                      clin_manager)
        # all users can read and update (their own) User records...
        models.TableAccess.create(self.usermodelname,
                                  models.TableAccess.TA_CRUD_UPDATE,
                                  every_user)
        models.TableAccess.create(self.usermodelname,
                                  models.TableAccess.TA_CRUD_READ,
                                  every_user)

        # now create a record-level rule
        FSM_filename = "User-UPD.yaml"
        UPDATE_OP = models.TableAccess.TA_CRUD_UPDATE
        fsmref = models.FSMTableRef.create("User-UPD-FSM", FSM_filename)
        ra = models.RecordAccess.create(self.usermodelname, UPDATE_OP, fsmref)
        assert ra is not None, "create record access failed"

        # predefine some access dicts that we can use later in the tests...
        # we always have two versions of these: client side and server side.
        self.client_side_jane_manager_read_acc_dct = dict(userId=self.jane_id,
                                                          userRole=dataelements.ROLE_MANAGER,
                                                          CRUDOp=serversocketbase.CRUD_read,
                                                          modelName=self.usermodelname)

        self.server_side_jane_manager_read_acc_dct = dict(userId=self.jane_id,
                                                          userRole=models.UserRoleTag.UR_MANAGER,
                                                          CRUDOp=models.TableAccess.TA_CRUD_READ,
                                                          modelName=self.usermodelname)

        self.client_side_john_user_read_acc_dct = dict(userId=self.john_id,
                                                       userRole=dataelements.ROLE_USER,
                                                       CRUDOp=serversocketbase.CRUD_read,
                                                       modelName=self.usermodelname)

        self.server_side_john_user_read_acc_dct = dict(userId=self.john_id,
                                                       userRole=models.UserRoleTag.UR_USER,
                                                       CRUDOp=models.TableAccess.TA_CRUD_READ,
                                                       modelName=self.usermodelname)
        print("setUpDB OK")

    def _tup_to_dct_profile(self, dt):
        un, fn, ln, em, is_log_in, loc = dt
        return collections.OrderedDict(username=un, firstName=fn,
                                       lastName=ln, email=em,
                                       profile=collections.OrderedDict(isLoggedIn=is_log_in,
                                                                       location=loc))

    def _tup_to_dct_flat(self, dt):
        """NOTE: this version has a flat hierarchy: no profile subdict"""
        un, fn, ln, em, is_log_in, loc = dt
        return collections.OrderedDict(username=un, firstName=fn,
                                       lastName=ln, email=em,
                                       isLoggedIn=is_log_in,
                                       location=loc)


class testserver_socket(base_server_socket):
    """A server_socket class for testing under CPython.
    The idea is that send() passes a request to the server via calling
    consuers.handle_msgdct().
    The message is converted to and from json, mimicking what happens when
    the data is sent over a real communication channel.
    The resulting response is passed to all listeners, again mimicking the
    standard server_socket behaviour.
    """
    def __init__(self, idstr: str, username: str) -> None:
        super().__init__(idstr)
        self._username = username

    def send(self, d_in) -> None:
        """Convert the data structure to JSON before sending it
        to the server by calling consumers.handle_mgsdct.
        Boradcast the server response to all listeners."""
        # for more rigorous testing, we also convert to json and back again
        # as this also ensures that all data structures are serialisable and
        # can be sent over the wire
        new_d_in = consumers.fromjson(consumers.tojson(d_in))
        res_dct = consumers.handle_msgdct(self._username, new_d_in)
        # lets pretend the server has returned right away --> pass the response back
        self.sndMsg(base.MSGD_SERVER_MSG, res_dct)


class test_observer(base.base_obj):
    """A class that can be used to ensure that events are being produced by a
    given object to be tested.
    e.g. sockets and data_cache are producing the expected events for the controller.
    This class keeps a record of all message events received.
    """
    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.reset()

    def rcvMsg(self, whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: base.MSGdata_Type) -> None:
        print("TEST_OBSERVER RCVMSG!")
        self._msgstack.append((whofrom, msgdesc, msgdat))

    def reset(self):
        self._msgstack = []

    def num_events(self):
        return len(self._msgstack)

    def printevents(self) -> None:
        fmtstr = "%10s %10s %s"
        print("message stack\n", fmtstr % ("sender", "event", "data"))
        print("\n".join([fmtstr % t for t in reversed(self._msgstack)]))


class SimpleDataCacheSetupMixin(SimpleDBSetupMixin):
    """Set up a database with some data in it, then initialise a data_cache
    which communicates with the graphql server over a dummy websocket.
    The datacache can be accessed in the tests by self.dc """
    def setUpDataCache(self):
        # put some data into thedatabase
        self.setUpDB()
        # now initialise the datacache
        username = self.jane_username
        ws = testserver_socket("bla-idstr", username)
        self.dc = dataelements.data_cache("datacache1", ws)
        assert self.dc is not None, "failed to instantiate a data_cache"
        self.dc.hello_server()
        modelname = self.usermodelname
        mod_name_lst = self.dc.known_model_names()
        assert len(mod_name_lst) > 0, "no known models in cache!"
        if modelname not in mod_name_lst:
            print("User modelname '{}' not defined in cache!".format(modelname))
            print("model name list: {}".format(" ,".join(mod_name_lst)))
            raise RuntimeError('no user model found')
