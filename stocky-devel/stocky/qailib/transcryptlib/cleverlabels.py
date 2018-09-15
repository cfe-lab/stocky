
import typing
# import qailib.common.base as base
# import qailib.transcryptlib.genutils as genutils
import qailib.transcryptlib.htmlelements as htmlelements


STARATTR_ONCLICK = htmlelements.base_element.STARATTR_ONCLICK

class ToggleLabel(htmlelements.label):
    """A label that can be toggled between two states (alternate text and HTML attributes).
    The initial state is the A state.

    NOTE: Our strategy to toggle the state on button click is to hijack
    the htmlelements.generic_element._clickfunc()
    """
    _DOTOGGLE = 'dotoggle'

    def __init__(self, parent: htmlelements.base_element,
                 idstr: str,
                 attrdctA: typing.Optional[dict],
                 labeltextA: str,
                 attrdctB: typing.Optional[dict],
                 labeltextB: str) -> None:
        attrdctA = attrdctA or {}
        attrdctB = attrdctB or {}
        dd = dict(msg=ToggleLabel._DOTOGGLE)
        attrdctB[STARATTR_ONCLICK] = attrdctA[STARATTR_ONCLICK] = dd
        htmlelements.label.__init__(self, parent, idstr, attrdctA, labeltextA, None)
        self.is_astate = True
        self.attdct: typing.Dict[bool, dict] = {True: attrdctA, False: attrdctB}
        self.txtdct: typing.Dict[bool, str] = {True: labeltextA, False: labeltextB}

    def set_state(self, toAstate: bool) -> None:
        """Set the visible state."""
        if self.is_astate != toAstate:
            self.toggle_state()

    def toggle_state(self) -> None:
        oldstate = self.attdct[self.is_astate]
        self.is_astate = not self.is_astate
        newstate = self.attdct[self.is_astate]
        newtext = self.txtdct[self.is_astate]
        self.rem_attrdct(oldstate)
        self.add_attrdct(newstate)
        self.setInnerHTML(newtext)

    def is_A_state(self) -> bool:
        """Return is A state? """
        return self.is_astate

    def _clickfunc(self):
        """This function is called whenever the user clicks on this label.
        We use it to change our visible appearance, then pass the click event along
        as if nothing had happened...
        """
        print("TOGGLE CLICKFUNC")
        self.toggle_state()
        super()._clickfunc()


class SimpleFSM:
    def __init__(self, numstates: int, event_lst: typing.List[str])-> None:
        """The event lst is a list of strings that describe the legal events that can happen"""
        self.numstates = numstates
        self.event_dct = dict([(ev, 1) for ev in event_lst])

    def get_init_state(self) -> int:
        """Return the initial state of the FSM."""
        print("SimpleFSM.get_init_state not overriden.")
        return None

    def get_new_state(self, curstate: int, event: str) -> int:
        """Given the current state and an event that has
        occurred (information provided in self.os)
        determine the new_state"""
        print("SimpleFSM.get_new_state not overriden.")
        return None

class FSMLabel(htmlelements.label):
    """A label whose states is controlled by a FSM.
    Each state will have alternate text and HTML attributes.

    NOTE: Our strategy to toggle the state on button click is to hijack
    the htmlelements.generic_element._clickfunc()
    """
    _DOTOGGLE = 'dotoggle'

    def __init__(self, parent: htmlelements.base_element,
                 idstr: str,
                 fsm: SimpleFSM,
                 state_attrdct: typing.Dict[int, typing.Tuple[str, dict]]) -> None:
        self.fsm = fsm
        self.state_attrdct = state_attrdct
        dd = dict(msg=ToggleLabel._DOTOGGLE)
        for labeltxt, attrdct in state_attrdct.values():
            attrdct[STARATTR_ONCLICK] = dd
        # determine the initial state from the FSM and set it
        self.curstate = fsm.get_init_state()
        labeltxt, attrdct = state_attrdct[self.curstate]
        htmlelements.label.__init__(self, parent, idstr, attrdct, labeltxt, None)

    def enter_event(self, newevent: str) -> None:
        """Set the visible state, based on the current event.
        The new state is determined by the FSM."""
        newstate = self.fsm.get_new_state(self.curstate, newevent)
        if self.curstate != newstate:
            self._toggle_state(newstate)

    def _toggle_state(self, newstate: int) -> None:
        oldtxt, oldattr = self.state_attrdct[self.curstate]
        self.curstate = newstate
        newtxt, newattr = self.state_attrdct[self.curstate]
        self.rem_attrdct(oldattr)
        self.add_attrdct(newattr)
        self.setInnerHTML(newtxt)

    def get_current_state(self) -> int:
        """Return the current state"""
        return self.curstate

    def _clickfunc(self):
        """This function is called whenever the user clicks on this label.
        We use it to change our visible appearance, then pass the
        click event along as if nothing had happened...
        """
        print("TOGGLE CLICKFUNC")
        self.enter_event(FSMLabel._DOTOGGLE)
        super()._clickfunc()
