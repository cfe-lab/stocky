
import typing
import qailib.common.base as base
# import qailib.transcryptlib.genutils as genutils


#   type definitions: transcrypt 3.6.49 fails with this
# blatype: GraphQLQueryType = NewType('GraphQLQueryType', str)
# BLAtype:
# blutype:
# this fails also: GraphQLQueryType = TypeVar('GraphQLQueryType')

GraphQLQueryType = str
GraphQLResponseType = dict


# CRUD = create, read, update, delete
CRUDMode = str

# These are predefined constants for the CRUD operations
# CRUD = create, read, update and delete
# These values must agree with similar definitions on the
# server side defined in webqai.models.
CRUD_create = CRUDMode('CREATE')
CRUD_read = CRUDMode('READ')
CRUD_update = CRUDMode('UPDATE')
CRUD_delete = CRUDMode('DELETE')

# the graphql requests that mutate the database
# NOTE: no frozenset support in transcrypt
# NOTE: we cannot use alst + blst in transcrypt
# (compiler bug, see issue https://github.com/QQuick/Transcrypt/issues/418
#
_mut_lst = [CRUD_create, CRUD_update, CRUD_delete]
_allcrud_lst = [CRUD_create, CRUD_update, CRUD_delete, CRUD_read]
mutation_qmode_set = set(_mut_lst)
# allowed_qmode_set = set(_mut_lst + [CRUD_read])
allowed_qmode_set = set(_allcrud_lst)


CRUD_string_table: typing.Dict[CRUDMode, str] = {CRUD_create: 'create',
                                                 CRUD_read: 'read',
                                                 CRUD_update: 'update',
                                                 CRUD_delete: 'delete'}


def createGQLDict_for_server(query_mode: CRUDMode,
                             query: GraphQLQueryType,
                             variable_dct: dict) -> dict:
    """Create a dictionary that contains all elements of a GraphQL query.
    Such a data structure would be send to the graphQL server, e.g. by a websocket.
    """
    qdct: typing.Dict[str, typing.Union[str, bool, CRUDMode, dict]]
    # log("CC '{}".format(query))
    qdct = {'cmd': 'graphql', 'query': query, 'qmode': query_mode}
    if variable_dct is not None:
        if "__kwargtrans__" in variable_dct:
            del variable_dct["__kwargtrans__"]
        qdct["graphql-var"] = variable_dct
    return qdct


def createGQLResponse_from_server(query_mode: CRUDMode,
                                  query_res) -> GraphQLResponseType:
    """Create a response dictionary from a response that graphene.Schema.execute() has produced.
    This response dict can be sent to a client e.g. over a websocket.
    """
    newmsg: typing.Dict[str, typing.Optional[typing.Union[str, bool]]] = {'type': 'graphql-resp',
                                                                          'qmode': query_mode}
    if query_res.errors is None:
        request_ok = True
        errmsg = None
        req_data = query_res.data
    else:
        request_ok = False
        errmsg = str(query_res.errors)
        req_data = None
    newmsg['send_to_group'] = (query_mode in mutation_qmode_set) and request_ok
    newmsg['ok'] = request_ok
    newmsg['data'] = req_data
    newmsg['errmsg'] = errmsg
    # newmsg['timestamp'] = genutils.nowstring()
    # newmsg['timestamp'] = "the time is 'now'"
    return newmsg


class base_server_socket(base.base_obj):
    def __init__(self, idstr):
        super().__init__(idstr)

    def send(self, data_to_server) -> None:
        print("base_server_socket: NOT sending {}".format(data_to_server))

    def issueGraphQLQuery(self,
                          query_mode: CRUDMode,
                          query: GraphQLQueryType,
                          variable_dct: dict) -> bool:
        """Issue a GraphQL query to the server. The response is returned as
        a JSON message to be read by the on_message_JSON callback.

        query_mode must be one of four values defined above. These are used
        to determine whether a query contains a mutation (that changes the database
        on the server) or a simple read operation.

        The two optional variable_dct and context_dct contain a Dict[str, Any]
        of graphQL variables.
        """
        # log(" issue {}".format(query))
        # log("CC2 {}".format(qdct))
        # log("Qdict {}".format(qdct))
        self.send(createGQLDict_for_server(query_mode, query, variable_dct))
        return True

    def on_message_JSON(self, data_from_server) -> None:
        """This is called with a javascript data structure whenever the client
        receives a message from the server.
        Here, we pass the message to any observers listening.
        """
        # NOTE: we must convert the javascript data into a python dict
        msg_dct = dict(data_from_server)
        # msg_dct = self.pythonify_dct(data_from_server)
        # log("server says: '{}'".format(msg_dct))
        self.sndMsg(base.MSGD_SERVER_MSG, msg_dct)
        # print("serversocketbase: swallowing server message {}".format(data_from_server))
