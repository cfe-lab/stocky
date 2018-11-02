"""Define a base_obj that provide the observer mechanism used by all other classes.
      This module is designed to be compiled by both Cpython and Transcrypt.
"""

import typing


# MSG_Type = typing.NewType('MSG_Type', typing.Union[str, dict])
# this leads to a runtime error in 3.6.49
# MSG_Type = typing.Union[str, dict]
# just declare it a string for now, and accept mypy errors.
MSGdesc_Type = str
# MSG_Type = typing.TypeVar('MSG_Type', str, dict)
MSGdata_Type = dict

# some predefined MSGdesc_Type strings
MSGD_DEFAULT = MSGdesc_Type("MSG_DEFAULT")

# message from the server has been received. Produced by serversocket.server_socket
MSGD_SERVER_MSG = MSGdesc_Type("MSG_SERVER_MSG")


# the server is passing on some data from the RFID scanner
MSGD_RFID_CLICK = MSGdesc_Type("MSG_RFID_CLICK")


# Indicate websocket communication from the webclient's perspective.
# These messages are produced by serversocket.server_socket
# the websocket communication to the server has come online/ offline.
MSGD_COMMS_ARE_UP = MSGdesc_Type("MSG_COMMS_ARE_UP")
MSGD_COMMS_ARE_DOWN = MSGdesc_Type("MSG_COMMS_ARE_DOWN")

MSGD_DATA_CACHE_READY = MSGdesc_Type("MSG_DATA_CACHE_READY")

# a 'logging' message is being passed along. This can be used to pass along
# error messages, for example.
MSGD_LOG_MESSAGE = MSGdesc_Type("MSG_LOG_MESSAGE")

# a button click event
MSGD_BUTTON_CLICK = MSGdesc_Type("MSG_BUTTON_CLICK")


# a input form has verified the input fields successfully and has data ready to pass along.
MSGD_FORM_SUBMIT = MSGdesc_Type("MSG_FORM_SUBMIT")

# a popup is about to open, and some elements might want to initialise their fields
# that are about to be displayed.
MSGD_POPUP_OPENING = MSGdesc_Type("MSG_POPUP_OPENING")

# a class has changed its state (e.g. on /off status) and wants to tell others
MSGD_STATE_CHANGE = MSGdesc_Type("MSG_STATE_CHANGE")

# a new data element has been created
MSGD_CRUD_CREATE = MSGdesc_Type("MSG_CRUD_CREATE")
MSGD_CRUD_UPDATE = MSGdesc_Type("MSG_CRUD_UPDATE")
MSGD_CRUD_DELETE = MSGdesc_Type("MSG_CRUD_DELETE")

MSGD_CRUD_OPS = [MSGD_CRUD_CREATE, MSGD_CRUD_UPDATE, MSGD_CRUD_DELETE]

MSGD_VALUE_CHANGE = MSGD_CRUD_UPDATE

# The object sending the message is about to be deleted
MSGD_DEAD_PARROT = MSGdesc_Type("MSG_DEAD_PARROT")


class base_obj:
    """A base class that provides a subscriber based observer mechanism
    between instances of objects.
    """

    def __init__(self, idstr: str) -> None:
        self._idstr = idstr or ""
        self._obsdct: typing.Dict[MSGdesc_Type, list] = {}

    def addObserver(self, observer: 'base_obj', msgdesc: MSGdesc_Type) -> None:
        """ Add an observer object to this class's list of dependent objects.

        In effect, the observer is 'subscribing' to any messages of msgdesc type
        that this instance emits in future.
        When this object sends a message self.sndMsg('msgdesc', msgdata)
        all of the observers who have registered for this kind of msgdesc
        will be called with rcvMsg(whofrom, 'msgdesc', msgdat)

        Args:
           observer: The instance that will be notified by this instance.
           msgdesc: The kind of message the observer is subscribing to.
        """
        if observer == self:
            print("BIG MISTAKE object observing itself")
        # obslst = self._obsdct[msgdesc]
        obslst = self._obsdct.setdefault(msgdesc, [])
        if observer not in obslst:
            obslst.append(observer)

    def remObserver(self, observer: 'base_obj', msgdesc: MSGdesc_Type) -> None:
        """Remove a previously added observer to a msgdesc type.

        This routine silently fails if the observer was not previously added.

        Args:
           observer: the observer to remove from this list of observers.
           msgdesc: the msg type the observer previously subscribed to.
        """
        obslst = self._obsdct.get(msgdesc, None)
        if obslst is not None:
            obslst.remove(observer)

    def sndMsg(self, msgdesc: MSGdesc_Type, msgdat: typing.Optional[MSGdata_Type]) -> None:
        """Send a message of a certain type (description) to all observers.

        Args:
           msgdesc: Describes the type of message
           msgdat: Includes additional data specific to the message
        """
        idstr = self._idstr or ""
        # print("SNDMSG: msg '{}' from '{}'".format(msgdesc, idstr))
        obslst = self._obsdct.get(msgdesc, [])
        for obs in obslst:
            whoto_id = obs._idstr or "empty_idstr"
            print("SNDMSG({}): sending msg '{}' to {}".format(idstr, msgdesc, whoto_id))
            obs.rcvMsg(self, msgdesc, msgdat)

    def rcvMsg(self,
               whofrom: 'base_obj',
               msgdesc: MSGdesc_Type,
               msgdat: typing.Optional[MSGdata_Type]) -> None:
        """The callback function used to receive a message from an observed object.

        This method should be overridden in the sub-classes in order to respond
        to a change event from an object that is being observed.
        Here, we just log information to the console so that un-handled messages
        can be found easily.

        Args:
           whofrom: the instance sending the message
           msgdesc: the kind of message being sent
           msgdat: additional data specific to the message
        """
        idstr = "empty_idstr" or self._idstr
        fromid = whofrom._idstr or "empty_whofrom"
        print("EMPTY RCV MSG obj '{}' received msg '{}' from '{}'".format(idstr, msgdesc, fromid))

    def relayMsg(self, whofrom: 'base_obj',
                 msgdesc: MSGdesc_Type,
                 msgdat: typing.Optional[MSGdata_Type]) -> None:
        """Pass on a message as if it came from whofrom, rather than from self.

        This routine sends messages to all observer subscribed **to this instance**
        as if the message came from another instance (whofrom).

        Args:
           whofrom: the instance we are posing as.
           msgdesc: the kind of message being sent.
           msgdat: additional data specific to the message
        """
        obslst = self._obsdct.get(msgdesc, [])
        for obs in obslst:
            obs.rcvMsg(whofrom, msgdesc, msgdat)
