
# Define the data model elements
import typing
import qailib.common.base as base
import qailib.common.serversocketbase as serversocketbase


def rec_copy(d: dict) -> dict:
    """Local replacement for copy.deepcopy(), as transcrypt cannot import the copy module.
    We recursively make a copy of a dict.
    This code can only handle values that are dicts or scaler types
    """
    newdct = dict()
    for k, v in d.items():
        if isinstance(v, dict):
            newdct[k] = rec_copy(v)
        else:
            newdct[k] = v
    return newdct


# User roles. these must match those used in the GraphQL interface
ROLE_MANAGER = 'MANAGER'
ROLE_LAB_ADMIN = 'LAB_ADMIN'
ROLE_USER = 'USER'
ROLE_IT_ADMIN = 'IT_ADMIN'

_role_lst = [ROLE_MANAGER, ROLE_LAB_ADMIN, ROLE_USER, ROLE_IT_ADMIN]
allowed_role_set = set(_role_lst)

# We also define a type for better documentation and type checking
Role_String_Type = str


# __pragma__ ('ifndef', 'sco_for_TS')
# These are type definitions of dictionaries that represent a collection of methods to
# implement CRUD: create, read, update and delete.
# transcrypt 3.6.54 does not support type definitions, so we have to use pragmas to remove them
in_CRUD_table = typing.Dict[serversocketbase.CRUDMode,
                            typing.Tuple[str, typing.Callable[[serversocketbase.CRUDMode, dict], bool]]]
out_CRUD_table = typing.Dict[serversocketbase.CRUDMode, typing.Callable[[serversocketbase.CRUDMode, dict], bool]]
# __pragma__ ('endif')


class record(base.base_obj):
    """A class that holds all attributes of an instance of a model.
    """
    def __init__(self, idstr: str, init_data_dct: dict) -> None:
        super().__init__(idstr)
        self._dct = init_data_dct

    def _setval_fromdb(self, newvaldct: dict) -> bool:
        """This method is used to change the record attributes when they have changed
        on the database.
        Return := 'at least one attribute has changed'
        """
        has_changed, curdct = False, self._dct
        for k, v in newvaldct.items():
            if curdct.get(k, None) != v:
                curdct[k] = v
                has_changed = True
        return has_changed

    def __getitem__(self, id: str) -> typing.Any:
        """This overrides the [] operator for this class"""
        # return self._dct.get(id, None)
        return self._get_dotted(self._dct, id)

    def __getattr__(self, name: str) -> typing.Any:
        """This implements 'dot' access."""
        return self._get_dotted(self._dct, name)
        # return self._dct.get(name, None)

    def gettyval(self, name: str) -> typing.Any:
        return self._get_dotted(self._dct, name)

    def __str__(self):
        return "record: {}".format(str(self._dct))

    def get_as_string(self, name: str) -> str:
        """Return this data element as a string for display"""
        return str(self._get_dotted(self._dct, name))

    def get_as_dict(self) -> dict:
        return rec_copy(self._dct)
        # return copy.deepcopy(self._dct)

    def _get_dotted(self, dct: dict, key: str) -> typing.Any:
        """Retrieve an element that has a key in the 'dotted form',
        i.e. subelements denoted by a dot (e.g. "profile.location"
        """
        kl = key.split(".")
        dd = dct
        i, ndepth = 0, len(kl)
        val, i = dd.get(kl[i], None), i+1
        while i < ndepth and val is not None:
            dd = val
            val, i = dd.get(kl[i], None), i+1
        return val


class base_record_table(base.base_obj):
    """A class that holds all records of a certain model class.
    (This corresponds to a database table)

    This class must initialise two CRUD_tables:
    incoming_crud: that handles CRUD requests from the *server side*
    outgoing_crud: that handles CRUD requests from the 'web client side*
    """
    def __init__(self,
                 table_name: str,
                 dc: "data_cache") -> None:
        super().__init__(table_name)
        self._tabname = table_name
        self._rectab: typing.Dict[str, record] = {}
        self._record_field = table_name
        self.dc = dc

    def _set_CRUD(self, in_CRUD: in_CRUD_table, out_CRUD: out_CRUD_table) -> None:
        self._incrud = in_CRUD
        self._outcrud = out_CRUD

    def do_out_CRUD(self, qmode: serversocketbase.CRUDMode, selector_dct: dict) -> bool:
        """Perform the outgoing CRUD operation for this table.
        Return := 'the CRUD operation was issued without error'
        """
        myfunc = self._outcrud.get(qmode, None)
        if myfunc is None:
            self.dc._log_error(data_cache.RET_RT_NO_FUNC, 'missing CRUD function')
            return False
        return myfunc(qmode, selector_dct)

    def __getitem__(self, id: str) -> record:
        """This overrides the [] operator for this class"""
        return self._rectab.get(id, None)

    def __getattr__(self, id: str) -> record:
        return self._rectab.get(id, None)

    def get_list(self,):
        """Return a list of all records in the table, in no particular order."""
        return self._rectab.values()

    def _add_new_items(self, dat_lst: list, must_create: bool, lverb: bool) -> bool:
        """Add items to this table of records.
        must_create := 'a clash in ids' between existing and new records is considered
        an error.'
        """
        new_rec_lst, mod_rec_lst = [], []
        for itm_dct in dat_lst:
            new_itm_id = itm_dct.get('id', None)
            if new_itm_id is None:
                self.dc._log_error(data_cache.RET_RT_CREATE_ID_IS_MISSING,
                                   "record missing an id: '{}'".format(itm_dct))
                return False
            if lverb:
                print('gotcha {}'.format(new_itm_id))
            old_rec = self._rectab.get(new_itm_id, None)
            if old_rec is None:
                new_rec = record(new_itm_id, itm_dct)
                self._rectab[new_itm_id] = new_rec
                new_rec_lst.append(new_rec)
            else:
                # we have a double entry
                if must_create:
                    self.dc._log_error(data_cache.RET_RT_CREATE_ALREADY_EXISTS,
                                       "record with id {} already in table {}".format(new_itm_id,
                                                                                      self._rectab[new_itm_id]))
                    return False
                else:
                    # we can update the old_rec...
                    mod_rec_lst.append(old_rec)
                    has_changed = old_rec._setval_fromdb(itm_dct)
                    if has_changed:
                        upd_dct = dict(desc=self._tabname, data=[old_rec])
                        old_rec.sndMsg(base.MSGD_CRUD_UPDATE, upd_dct)
                        self.sndMsg(base.MSGD_CRUD_UPDATE, upd_dct)
        success = len(new_rec_lst) + len(mod_rec_lst) == len(dat_lst)
        if success:
            if lverb:
                print("created {} new records".format(len(new_rec_lst)))
            # now notify our observers
            self.sndMsg(base.MSGD_CRUD_CREATE, dict(desc=self._tabname,
                                                    data=new_rec_lst))
        return success

    def read_from_db(self, qmode: serversocketbase.CRUDMode, dd: dict) -> bool:
        """This is called when the server has sent records we need to cache.
        Create new records and insert them into self._rectab.
        Return := 'insertion was successful'
        If a record sent already exists in the cache, then this is NOT considered
        an error.
        """
        lverb = False
        dat_lst = dd.get('data', None) or dd.get('input', None)
        if dat_lst is None:
            self.dc._log_error(data_cache.RET_RT_DATA_MISSING,
                               "data field missing in incoming message {}".format(dd))
            return False
        if lverb:
            print("READfromsb: dat_lst {}".format(dat_lst))
            print("table size before insert: {}".format(len(self._rectab)))
        return self._add_new_items(dat_lst, False, lverb)

    def create_from_db(self, qmode: serversocketbase.CRUDMode, dd: dict) -> bool:
        """This is called when the server has sent new records to be created from
        scratch.
        """
        lverb = True
        data = dd.get('data', None) or dd.get('input', None)
        if data is None:
            self.dc._log_error(data_cache.RET_RT_DATA_MISSING,
                               "data field missing in incoming message {}".format(dd))
            return False
        if lverb:
            print("CREATE_CB  {}".format(data))
            print("table size before insert: {}".format(len(self._rectab)))
        new_item = data
        if new_item is None:
            self.dc._log_error(data_cache.RET_RT_CREATE_RECORD_NAME_MISSING,
                               "create failed with missing data")
            return False
        return self._add_new_items([new_item], True, lverb)

    def delete_from_db(self, qmode: serversocketbase.CRUDMode, dd: dict) -> bool:
        lverb = True
        data = dd.get('data', None) or dd.get('input', None)
        if data is None:
            self.dc._log_error(data_cache.RET_RT_DATA_MISSING,
                               "data field missing in incoming message {}".format(dd))
            return False
        if lverb:
            print("DELETE_CB  {}".format(data))
            print("table size before delete: {}".format(len(self._rectab)))
        id_str = data
        rec_to_del = self._rectab.get(id_str, None)
        if rec_to_del is None:
            return False
        # warn any dependants of this record that is going to cease to exist
        rec_to_del.sndMsg(base.MSGD_DEAD_PARROT, {})
        del self._rectab[id_str]
        self.sndMsg(base.MSGD_CRUD_DELETE, dict(desc=self._tabname,
                                                data=[rec_to_del]))
        return True

    def update_from_db(self, qmode: serversocketbase.CRUDMode, dd: dict) -> bool:
        lverb = False
        data = dd.get('data', None) or dd.get('input', None)
        if data is None:
            self.dc._log_error(data_cache.RET_RT_DATA_MISSING,
                               "data field missing in incoming message {}".format(dd))
            return False
        if lverb:
            print("UPDATE_CB  {}".format(data))
            print("table size before update: {}".format(len(self._rectab)))
        new_val_dct = data.get(self._record_field, None)
        new_val_dct = data
        if new_val_dct is None:
            self.dc._log_error(data_cache.RET_RT_UPDATE_DATA_IS_NONE,
                               "update failed: data is None")
            return False
        id_str = new_val_dct.get('id', None)
        if id_str is None:
            self.dc._log_error(data_cache.RET_RT_UPDATE_ID_MISSING,
                               "update: id field missing")
            return False
        rec_to_mod = self._rectab.get(id_str, None)
        if rec_to_mod is None:
            self.dc._log_error(data_cache.RET_RT_UPDATE_NO_SUCH_RECORD,
                               "update: record to update (id={}) not found".format(id_str))
            return False
        has_changed = rec_to_mod._setval_fromdb(new_val_dct)
        if has_changed:
            upd_dct = dict(desc=self._tabname, data=[rec_to_mod])
            rec_to_mod.sndMsg(base.MSGD_CRUD_UPDATE, upd_dct)
            self.sndMsg(base.MSGD_CRUD_UPDATE, upd_dct)
        if lverb:
            print("update_cb: returning True")
        return True

    def generic_intable(self, modelname) -> in_CRUD_table:
        """Create an in_CRUD_table for a record_table with the given name.
        This is called 'generic' because the 'standard' methods are allocated
        to the CRUD operations.
        The 'standard' methods are self.create_from_db, self.read_from_db, etc.
        """
        methtab = {serversocketbase.CRUD_create: self.create_from_db,
                   serversocketbase.CRUD_read: self.read_from_db,
                   serversocketbase.CRUD_update: self.update_from_db,
                   serversocketbase.CRUD_delete: self.delete_from_db}
        rdct: in_CRUD_table = {}
        for crudmode, crud_prefix in serversocketbase.CRUD_string_table.items():
            rdct[crudmode] = ("{}{}".format(crud_prefix, modelname), methtab[crudmode])
        return rdct


class GQL_record_table(base_record_table):
    def __init__(self,
                 table_name: str,
                 dc: "data_cache") -> None:
        base_record_table.__init__(self, table_name, dc)
        # register our in_CRUD entries with the data_cache
        for crud_op, tup in self._incrud.items():
            opstr, opfunc = tup
            dc._registerOP(crud_op, opstr, opfunc)


class LocalRecordTable(base_record_table):
    """A record table that controls a number of variables that are local to the client,
    i.e. are not stored on the database.
    Each variable must have a unique key and be of type base.base_obj .

    NOTE: we implement this by implementing all outgoing CRUD operations locally
    instead of send operations to a server. This is done in do_out_CRUD.
    The incoming CRUD table is empty, as we will not be getting any server updates
    for locally held variables.
    """
    def __init__(self,
                 table_name: str,
                 dc: "data_cache") -> None:
        o_crud: out_CRUD_table = {serversocketbase.CRUD_read: self.read_from_db,
                                  serversocketbase.CRUD_create: self.create_from_db,
                                  serversocketbase.CRUD_delete: self.delete_from_db,
                                  serversocketbase.CRUD_update: self.update_from_db}
        self._set_CRUD(None, o_crud)
        super().__init__(table_name, dc)


class Generic_RT(GQL_record_table):

    def __init__(self, modelname: str, dc: "data_cache", is_dct: dict) -> None:
        i_crud: in_CRUD_table = self.generic_intable(modelname)
        # outgoing: we send requests to the server
        self._otab = is_dct
        o_crud: out_CRUD_table = {serversocketbase.CRUD_read: self.do_sq,
                                  serversocketbase.CRUD_create: self.do_sq,
                                  serversocketbase.CRUD_delete: self.do_sq,
                                  serversocketbase.CRUD_update: self.do_sq}
        self._set_CRUD(i_crud, o_crud)
        super().__init__(modelname, dc)

    def do_sq(self, qmode: serversocketbase.CRUDMode, kwargs: dict) -> bool:
        return self._hidden_do_sq(self._otab[qmode], kwargs)

    def _hidden_do_sq(self, qfunc_dct: dict, kwargs: dict) -> bool:
        """Perform a server query using information from the qfunc_dct.
        kwargs is a dict that describes the input arguments to the query.
        """
        crudmode = qfunc_dct['CRUDmode']
        qstr = qfunc_dct['qs']
        # access kwargs here: must have the socket and the single graphql function input argument
        sock: serversocketbase.base_server_socket = kwargs['ws']
        # REMINDER: our functions have a SINGLE input argument (typically called 'input')
        # which is a record with a number of attributes.
        # we expect a dict that has an entry called 'input' which then has required attributes.
        argname = qfunc_dct['input_arg_name']
        # does kwargs have an entry with the required name ?
        input_dct = kwargs.get(argname, None)
        if input_dct is None:
            self.dc._log_error(data_cache.RET_RT_MISSING_INPUT_ARG,
                               "function input argument '{}' is missing".format(argname))
            return False
        # input_dct: a dict with variables the client has provided as input for the graphQL query.
        # check them here for compatability after having remove the entry for the socket.
        # REMINDER: inarglst elements are a 3-tuple (varname, typename, is_non_null)
        inattrlst = qfunc_dct['inargs']
        have_names = set(input_dct.keys())
        known_names = set([vn for vn, tn, isreq in inattrlst])
        unknown_names = have_names - known_names
        if len(unknown_names) > 0:
            # unknown attribute names
            self.dc._log_error(data_cache.RET_RT_UNDEFINED_INPUT_ATTR,
                               "unknown input attributes {} (known attributes are {})".format(unknown_names,
                                                                                              known_names))
            return False
        must_have_names = set([vn for vn, tn, isreq in inattrlst if isreq])
        if not must_have_names.issubset(have_names):
            # a required variable is missing
            self.dc._log_error(data_cache.RET_RT_MISSING_NONNUL_INPUT_ATTR,
                               """
missing obligatory input attributes {} (required attributes are {})""".format(must_have_names - have_names,
                                                                              must_have_names))
            return False
        # NOTE: we skip checking for correct variable *types* here for now.
        did_it = sock.issueGraphQLQuery(crudmode,
                                        serversocketbase.GraphQLQueryType(qstr),
                                        {argname: input_dct})
        if not did_it:
            self.dc._log_error(data_cache.RET_RT_QUERY_FAIL, "RT query fail")
        return did_it


TS_VARNAME = "timestamp"


class data_cache(base.base_obj):
    """A class that holds all database data.
    This is essentially a dictionary of record_table
    """

    # These values are used in data_cache.exitcode
    RET_OK = 0
    RET_NO_TABLE = 1
    RET_MSG_INVALID = 2
    RET_UNKNOWN_MODEL = 3
    RET_ACCESS_NOT_SET = 4
    RET_INTROSPECTION_NOT_SET = 5

    # these are for CRUDOP failure on client or server (i.e. database)
    RET_CLNT_CRUDOP_FAILED = 20
    RET_SRV_CRUDOP_FAILED = 21
    RET_INVALID_QMODE = 22
    RET_SRV_INTSPEC_FAILED = 23
    RET_SRV_INTSPEC_MALFORMED = 24
    RET_SRV_DATACACHE_INIT_FAILED = 25

    # these are related to FORM requests
    RET_SRV_FORMREQ_FAILED = 40

    # RET_RT: error messages from record_table callback functions
    RET_RT_NO_FUNC = 100
    RET_RT_MISSING_INPUT_ARG = 101
    RET_RT_UNDEFINED_INPUT_ATTR = 102
    RET_RT_MISSING_NONNUL_INPUT_ATTR = 103
    RET_RT_QUERY_FAIL = 104
    RET_RT_DATA_MISSING = 105
    # RET_RT_create
    RET_RT_CREATE_SRV_FAILED = 106
    RET_RT_CREATE_RECORD_NAME_MISSING = 107
    RET_RT_CREATE_ALREADY_EXISTS = 108
    RET_RT_CREATE_ID_IS_MISSING = 109
    # RET_RT_update
    RET_RT_UPDATE_DATA_IS_NONE = 120
    RET_RT_UPDATE_ID_MISSING = 121
    RET_RT_UPDATE_NO_SUCH_RECORD = 122

    def __init__(self, idstr: str, ws: serversocketbase.base_server_socket) -> None:
        super().__init__(idstr)
        self._IN_CB_TAB: typing.Dict[typing.Tuple[serversocketbase.CRUDMode, str],
                                     typing.Callable[[serversocketbase.CRUDMode, dict], bool]] = {}
        self._ws = ws
        ws.addObserver(self, base.MSGD_SERVER_MSG)
        ws.addObserver(self, base.MSGD_COMMS_ARE_UP)
        self._introspect_ok = False
        self._access_is_set = False
        self.exitcode = data_cache.RET_OK
        self.errmsg = ""
        self._model_dct: typing.Dict[str, base_record_table] = {}
        self._model_dct['local'] = LocalRecordTable('local', self)
        self._guihashkey = self._datahashkey = "1234"
        self._formdefdct: typing.Dict[str, dict] = None

    def reserve_cache(self, modelname: str, selector_dct: dict) -> bool:
        """Load records of modelname using the provided selector from the database
        into the cache.
        NOTE: This function is asynchronous. It initiates a retrieval from the db, but does
        not return the data itself.
        It returns a boolean := 'the request was sent successfully'
        """
        if self._get_or_make_RT(modelname) is None:
            return False
        else:
            return self.issue_CRUD(serversocketbase.CRUD_read, modelname, selector_dct)

    def release_cache(self, modelname: str, selector=None) -> None:
        """Remove designated records from the cache.
        This does not delete any items from the database.
        """
        pass

    def addTableObserver(self, modelname: str, observer: base.base_obj) -> bool:
        """The observer object will receive a notification whenever any one of
        the CRUD operations are performed on this table.
        Return := 'observer has been added successfully'
        """
        rec_table = self._get_or_make_RT(modelname)
        if rec_table is None:
            return False
        else:
            for op_type in base.MSGD_CRUD_OPS:
                rec_table.addObserver(observer, op_type)
            return True

    def addRecordObserver(self, modelname: str, id: str,
                          observer: base.base_obj, msgdesc: base.MSGdesc_Type) -> bool:
        """The observer will receive a notification whenever the specified msgdesc event
        occurs on the record specified by (modelname, id).
        Return := 'observer was added successfully"
        """
        rec = self.get_record(modelname, id)
        if rec is None:
            return False
        rec.addObserver(observer, msgdesc)
        return True

    def _registerOP(self,
                    crudmode: serversocketbase.CRUDMode,
                    idstr: str,
                    cb_func: typing.Callable[[serversocketbase.CRUDMode, dict], bool]):
        """Register a record_table callback function. """
        k = (crudmode, idstr)
        self._IN_CB_TAB[k] = cb_func

    def _log_error(self, exitcode: int, errmsg: str) -> None:
        self.exitcode = exitcode
        self.errmsg = errmsg
        self.sndMsg(base.MSGD_LOG_MESSAGE, dict(exitcode=exitcode, errmsg=errmsg))

    def rcvMsg(self, whofrom: base.base_obj,
               msgdesc: base.MSGdesc_Type,
               msgdat: base.MSGdata_Type) -> None:
        """This method will be called whenever the serversocketbase.base_server_socket has
        a response from a previous query we have launched, or
        from a db update initiated from the server.
        """
        lverb = True
        if lverb:
            print("data_cache rcvMsg: {}: {}".format(msgdesc, msgdat))
        # decide what to do based on the msgdesc.
        if msgdesc == base.MSGD_SERVER_MSG:
            # message from the server.
            if msgdat is None:
                self._log_error(data_cache.RET_MSG_INVALID, "msgdat is None")
                return
            # self.set_local_var(TS_VARNAME, msgdat.get(TS_VARNAME, 'dunno'))
            # decide what to do based on the msg_type.
            msg_type = msgdat.get("type", None)
            if msg_type == 'graphql-resp':
                self.data_update(msgdat)
            elif msg_type == 'datacache-init-resp':
                self._datacache_init(msgdat)
            # elif msg_type == 'form-request-resp':
            #    self._form_response(msgdat)
            else:
                # some sort of message we don't understand
                self._log_error(data_cache.RET_MSG_INVALID,
                                "unknown msg type {}".format(msg_type))
                return
        elif msgdesc == base.MSGD_COMMS_ARE_UP:
            # server has just come online...(re)establish contact
            self.hello_server()
        else:
            self._log_error(data_cache.RET_MSG_INVALID,
                            "don't know how to handle message {}".format(msgdesc))

    def _introspect_update(self, msg: dict, lverb=False) -> None:
        """We have received an introspection response from the server
        ==> lets update our models and CRUD tables from this information.
        """
        if lverb:
            print("INTROSPECT UPDATE {}".format(msg))
        if not msg.get('ok', False):
            self._log_error(data_cache.RET_SRV_INTSPEC_FAILED,
                            "introspect request failed on server")
            return
        hash_ok = msg.get('hash_ok', False)
        if hash_ok:
            # we are up-to-date and there is nothing to do
            self.exitcode = data_cache.RET_OK
            self.errmsg = ""
            return
        # the server has sent us an update with either introspection or gui tables, or both.
        ret_dct = msg.get('data', None)
        if ret_dct is None:
            self._log_error(data_cache.RET_SRV_INTSPEC_MALFORMED,
                            "Malformed intspec message: missing data")
            return
        intro_dct = ret_dct.get('introdct', None)
        if intro_dct is not None:
            # ==> use the introspection data to generate CRUD tables.
            server_data_hash = intro_dct.get('hash', None)
            intspec_lst = intro_dct.get('intspec', None)
            if server_data_hash is None or intspec_lst is None or len(intspec_lst) != 3:
                self._log_error(data_cache.RET_SRV_INTSPEC_MALFORMED,
                                "Malformed intspec message")
                return
            # now update our CRUD tables
            crud_tab, func_tab, self._formdefdct = intspec_lst
            for modelname, crud_dct in crud_tab.items():
                self._model_dct[modelname] = Generic_RT(modelname, self, crud_dct)
            self._datahashkey = server_data_hash
            self._crud_tab = crud_tab
            self._introspect_ok = True
        gui_dct = ret_dct.get('guidct', None)
        if gui_dct is not None:
            # extract the GUI information
            server_gui_hash = gui_dct.get('hash', None)
            gui_dct = gui_dct.get('guispec', None)
            if server_gui_hash is None or gui_dct is None:
                self._log_error(data_cache.RET_SRV_INTSPEC_MALFORMED,
                                "Malformed guispec message")
                return
            self._guihashkey = server_gui_hash
            # NOTE: actually do something with the guitab here
        # finally, set our state
        self.exitcode = data_cache.RET_OK
        self.errmsg = ""

    def _get_or_make_RT(self, modelname: str) -> base_record_table:
        if not self._introspect_ok:
            self._log_error(data_cache.RET_INTROSPECTION_NOT_SET,
                            "getormakeRT: introspection data not set")
            return None
        retval = self._model_dct.get(modelname, None)
        if retval is None:
            self._log_error(data_cache.RET_UNKNOWN_MODEL,
                            "getormakeRT: unknown model {}".format(modelname))
        return retval

    def _dump_crud_tab(self):
        print("CRUD_TABLE {}".format(self._crud_tab))
        crud_tab = self._crud_tab
        for modelname, crud_dct in crud_tab.items():
            print("Model {}".format(modelname))
            for crudop, dct in crud_dct.items():
                for k, v in dct.items():
                    print("   {}: {}".format(k, v))

    def hello_server(self):
        """This method is called whenever the connection to the server is established,
        or reestablished after a break.
        Send our introspection hash numbers to the server for checking.
        The server will respond with information, which the client will
        use to update its CRUD tables in _datachache_init."""
        print("hello server")
        self._ws.send(dict(cmd='datacache-init',
                           datahashkey=self._datahashkey,
                           guihashkey=self._guihashkey))

    def _datacache_init(self, topmsg) -> None:
        """We have received a response to a datacache-init request that we sent to
        the server in hello_server().
        ==> lets update our:
        a) user access record information
        b) introspection data
        c) User record tables.
        and signal (i.e. to the controller) that we are ready.
        """
        okval = topmsg.get('ok', False)
        if not okval:
            self._log_error(data_cache.RET_SRV_DATACACHE_INIT_FAILED,
                            topmsg.get('errmsg', "datacache: received ok=False from server"))
            return
        # topmsg will have three entries with subdicts
        # user information
        msgdat = topmsg.get('userinfo', None)
        userid = msgdat.get('id', None)
        username = self._my_username = msgdat.get('username', None)
        self.set_access_info(userid, ROLE_USER)
        self._my_username = username
        # now introspection
        intro_dct = topmsg.get('introspect', None)
        self._introspect_update(intro_dct)
        if self.exitcode != data_cache.RET_OK:
            print('introspect_update failed')
            return

        # now the user reserve_cache
        u_cache_data = topmsg.get('user_cache', None)
        self.data_update(u_cache_data)
        if self.exitcode != data_cache.RET_OK:
            print('data_update failed')
            return
        # if we get this far, we have succeeded
        print('datacache: reserve cache OK')
        self.sndMsg(base.MSGD_DATA_CACHE_READY, {})

    def get_user_info(self) -> typing.Tuple[str, str, str]:
        if self._access_is_set:
            return self._my_useridstr, self._my_username, self._my_current_role
        else:
            return None, None, None

    def data_update(self, msgdat) -> None:
        """We have received a response to a graphql request from the server
        ==> lets update our record tables.
        """
        ok_resp = msgdat.get("ok", False)
        if not ok_resp:
            # an operation that failed on the server
            self._log_error(data_cache.RET_SRV_CRUDOP_FAILED, msgdat.get("errmsg", ""))
            return
        qmode = msgdat.get('qmode', None)
        valid_qmode = qmode in serversocketbase.allowed_qmode_set
        if not valid_qmode:
            self._log_error(data_cache.RET_INVALID_QMODE,
                            "invalid qmode = '{}' not in '{}'".format(qmode,
                                                                      serversocketbase.allowed_qmode_set))
            return
        # here we are checking for entries in the encapsulated dict
        msg_data = msgdat.get("data", None)
        msg_data = dict(msg_data) if msg_data is not None else None
        if msg_data is None:
            # some sort of inconsistent message
            self._log_error(data_cache.RET_MSG_INVALID, "got data==None ?!")
            return
        # at this stage, the graphql request itself was successful, but the response might
        # still have been something like 'permission denied...'. For those errors,
        # we check the individual 'ok' flag below
        # print("DC UPD {}".format(msg_data))
        for tabname, tabdata in msg_data.items():
            cb_key = (qmode, tabname)
            # print("tabby '{}'".format(cb_key))
            # NOTE: some responses will have an 'ok' field in them.
            # If they do, and its false, then we know that an operation on
            # the server failed (e.g. 'permission denied')
            # => do not call any callback in that case.
            try:
                server_op_ok = tabdata.get("ok", True)
            except:
                server_op_ok = True
            if not server_op_ok:
                self._log_error(data_cache.RET_SRV_CRUDOP_FAILED,
                                tabdata.get('errmsg', "CRUDOP failed on server"))
                return
            cb_func = self._IN_CB_TAB.get(cb_key, None)
            if cb_func is None:
                self._log_error(data_cache.RET_NO_TABLE,
                                "INTERNAL ERROR: CRUD {} on table {}: no cb_func".format(qmode, tabname))
                return
            if not cb_func(qmode, dict(data=tabdata['retdata'])):
                # the exitcode should have been set in the CB function.
                # check for this, and set it to a generic value if it was not
                if self.exitcode == data_cache.RET_OK:
                    self._log_error(data_cache.RET_CLNT_CRUDOP_FAILED,
                                    "CRUD func for {} on table {} failed".format(qmode, tabname))
                return
        # if we get this far, we have succeeded
        self.exitcode, self.errmsg = data_cache.RET_OK, ""

    def set_access_info(self, my_useridstr: str, my_current_role: Role_String_Type) -> None:
        self._my_useridstr = my_useridstr
        self._my_current_role = my_current_role
        self._access_is_set = True

    def issue_CRUD(self,
                   qmode: serversocketbase.CRUDMode,
                   modelname: str,
                   input_dct: dict) -> bool:
        """Issue a CRUD event to the underlying model.
        input_dct: a dict containing fields (attributes) contained in the corresponding
        graphql function's input argument type, *except the access block*.
        The access block is added to the input_dct here from the previously
        set access info.
        Return a boolean := 'the CRUD event *was issued* successfully.'
        NOTE: as this is an asynchronous operation, a True value returned from here
        does not necessarily mean that the operation itself was *performed* successfully.
        """
        self.exitcode, self.errmsg = data_cache.RET_OK, ""
        rec_table = self._get_or_make_RT(modelname)
        if rec_table is None:
            return False
        if not self._access_is_set:
            self._log_error(data_cache.RET_ACCESS_NOT_SET,
                            "Access Info it not set. Do this before issue_CRUD()")
            return False
        access_dct = dict(userId=self._my_useridstr,
                          userRole=self._my_current_role,
                          CRUDOp=qmode,
                          modelName=modelname)
        if input_dct.get('FSMOp', None) is not None:
            access_dct['FSMOp'] = input_dct['FSMOp']
            del input_dct['FSMOp']
        input_dct['access'] = access_dct
        selector_dct = dict(ws=self._ws, input=input_dct)
        return rec_table.do_out_CRUD(qmode, selector_dct)

    def get_record(self, modelname: str, id: str) -> record:
        """Access a record from a table in the cache.
        The modelname defines the record table and id is the record id of that modelname.
        Return None if either the modelname or the record does not exist.
        """
        rec_table = self._get_or_make_RT(modelname)
        if rec_table is None:
            return None
        else:
            return rec_table[id]

    def known_model_names(self) -> typing.List[str]:
        """Return a list of known model names."""
        return list(self._model_dct.keys())

    def __getitem__(self, modelname: str) -> base_record_table:
        """This overrides the [] operator for this class and returns
        the record_table or None."""
        return self._model_dct.get(modelname, None)

    def __getattr__(self, modelname: str) -> base_record_table:
        """Access the recordtable in the cache using an attribute
        access (i.e. using the 'dot notation' a.b)
        Return the record_table or None."""
        return self._model_dct.get(modelname, None)

    def new_local_var(self, varname: str, varobj: typing.Any) -> bool:
        """Store a base_obj in the local data cache under the unique name 'varname'.
        A local variable is not stored on the server database.
        Return 'the local variable was stored successfully'
        """
        return self.issue_CRUD(serversocketbase.CRUD_create, 'local',
                               dict(dict(dict(id=varname, val=varobj))))

    def set_local_var(self, varname: str, new_vardata: typing.Any) -> bool:
        """Set the value of an existing local variable.
        Return 'the setting was successful'
        """
        return self.issue_CRUD(serversocketbase.CRUD_update, 'local',
                               dict(dict(dict(id=varname, val=new_vardata))))

    def known_formdef_model_names(self) -> typing.List[str]:
        """Return a list of all forminfo model names defined."""
        if not self._introspect_ok:
            self._log_error(data_cache.RET_INTROSPECTION_NOT_SET,
                            "known_forminfo_names: introspection data not set")
            return None
        return list(self._formdefdct.keys())

    def getFormDefDict(self, modelname: str, fdname: str) -> dict:
        """Return the dict which describes the record (fields and types) of
        the given model. This dict was detected from introspection on the server.
        """
        if not self._introspect_ok:
            self._log_error(data_cache.RET_INTROSPECTION_NOT_SET,
                            "getFormInfo: introspection data not set")
            return None
        mod_dct = self._formdefdct.get(modelname, None)
        if mod_dct is None:
            return None
        return mod_dct.get(fdname, None)
