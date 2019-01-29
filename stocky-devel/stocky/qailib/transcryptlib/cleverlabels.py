
import typing
import qailib.common.base as base
# import qailib.transcryptlib.genutils as genutils
import qailib.transcryptlib.htmlelements as htmlelements


STARATTR_ONCLICK = htmlelements.base_element.STARATTR_ONCLICK
STARATTR_ONCHANGE = htmlelements.base_element.STARATTR_ONCHANGE


class SliderSwitch(htmlelements.input_checkbox):
    _DOTOGGLE = 'dotoggle'

    def __init__(self, parent: htmlelements.base_element,
                 idstr: str,
                 attrdctA: typing.Optional[dict],
                 labeltextA: str,
                 attrdctB: typing.Optional[dict],
                 labeltextB: str) -> None:
        attrdctA = attrdctA or {}
        attrdctB = attrdctB or {}
        dd = dict(msg=SliderSwitch._DOTOGGLE)
        attrdctB[STARATTR_ONCHANGE] = attrdctA[STARATTR_ONCHANGE] = dd
        attrdctA["for"] = idstr
        self.laba = htmlelements.label(parent, "lla", attrdctA, labeltextA, None)
        check_attr: typing.Dict[str, str] = {}
        check_attr[STARATTR_ONCHANGE] = dd
        htmlelements.input_checkbox.__init__(self, parent, idstr, check_attr, None)
        attrdctB["for"] = idstr
        self.labb = htmlelements.label(parent, "llb", attrdctB, labeltextB, None)
        self.attA = attrdctA
        self.attB = attrdctB
        self.offattr = {'class': "w3-tag w3-light-gray w3-border"}

        self._set_hint(self.get_checked())

    def _set_hint(self, is_checked: bool):
        laba = self.laba
        labb = self.labb
        offattr = self.offattr
        if is_checked:
            # hi: labB, lo: labA
            labb.rem_attrdct(offattr)
            labb.add_attrdct(self.attB)
            laba.rem_attrdct(self.attA)
            laba.add_attrdct(offattr)
        else:
            # hi: labA, lo: labB
            laba.rem_attrdct(offattr)
            laba.add_attrdct(self.attA)
            labb.rem_attrdct(self.attB)
            labb.add_attrdct(offattr)

    def _changefunc(self):
        is_checked = self.get_checked()
        print("SliderSwitch CHANGEFUNC {}".format(is_checked))
        self._set_hint(is_checked)
        super()._changefunc()


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
        self.sndMsg(base.MSGD_STATE_CHANGE, dict(state=self.is_astate))

    def is_A_state(self) -> bool:
        """Return is A state? """
        return self.is_astate

    def _clickfunc(self):
        """This function is called whenever the user clicks on this label.
        We use it to change our visible appearance, then pass the click event along
        as if nothing had happened...
        """
        print("TOGGLE-label CLICKFUNC")
        self.toggle_state()
        super()._clickfunc()


class DropToggleLabel(htmlelements.select):
    """A label that can be toggled between two states (alternate text and HTML attributes).
    The initial state is the A state.

    This class is implemented as a select element with a drop-down selector.
    NOTE: Our strategy to toggle the state on button click is to hijack
    the htmlelements.select._changefunc()
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
        dd = dict(msg=DropToggleLabel._DOTOGGLE)
        attrdctB[STARATTR_ONCHANGE] = attrdctA[STARATTR_ONCHANGE] = dd
        htmlelements.select.__init__(self, parent, idstr, attrdctA, None)
        self.is_astate = True
        self.attdct: typing.Dict[bool, dict] = {True: attrdctA, False: attrdctB}
        # NOTE: we do not need to save the texts into a separate variable, instead, we just
        # use them as selectable options. When we toggle the values, we set the attribute
        # dicts explicitly
        self._iddct: typing.Dict[bool, str] = {}
        self._iddct[True] = 'blaA'
        self._iddct[False] = 'blaB'
        self.add_or_set_option('blaA', labeltextA)
        self.add_or_set_option('blaB', labeltextB)

    def set_state(self, toAstate: bool) -> None:
        """Set the visible state."""
        if self.is_astate != toAstate:
            self.toggle_state()

    def toggle_state(self) -> None:
        # print("TOGGLY!")
        oldstate = self.attdct[self.is_astate]
        self.is_astate = not self.is_astate
        newstate = self.attdct[self.is_astate]
        self.rem_attrdct(oldstate)
        self.add_attrdct(newstate)
        self.set_selected(self._iddct[self.is_astate])
        self.sndMsg(base.MSGD_STATE_CHANGE, dict(state=self.is_astate))

    def is_A_state(self) -> bool:
        """Return is A state? """
        return self.is_astate

    def _changefunc(self):
        """This function is called whenever the user clicks on this label.
        We use it to change our visible appearance, then pass the click event along
        as if nothing had happened...
        This will allow any instances listening to the base_element.STARATTR_ONCHANGE
        message to react to a value change as well.
        Note that toggle_state() also emits an MSGD_STATE_CHANGE message upon completion.
        """
        print("TOGGLE CHANGEFUNC")
        self.toggle_state()
        super()._changefunc()


class SimpleFSM(base.base_obj):
    def __init__(self, idstr: str, numstates: int, event_lst: typing.List[str])-> None:
        """The event lst is a list of strings that describe the legal events that can happen"""
        base.base_obj.__init__(self, idstr)
        self.numstates = numstates
        self.event_dct = dict([(ev, 1) for ev in event_lst])

    def get_init_state(self) -> int:
        """Return the initial state of the FSM."""
        print("SimpleFSM.get_init_state not overriden.")
        return -10000

    def get_new_state(self, curstate: int, event: str) -> int:
        """Given the current state and an event that has
        occurred (information provided in self.os)
        determine the new_state"""
        print("SimpleFSM.get_new_state not overriden.")
        return -10000


class FSMLabel(htmlelements.label):
    """A label whose states is controlled by an FSM.
    Each state will have alternate text and HTML attributes.

    NOTE: Our strategy to toggle the state on button click is to hijack
    the htmlelements.generic_element._clickfunc()
    """
    FSM_CLICK_EVENT = 'doclick'
    _DOTOGGLE = 'dotoggle'

    def __init__(self, parent: htmlelements.base_element,
                 idstr: str,
                 fsm: SimpleFSM,
                 state_attrdct: typing.Dict[int, typing.Tuple[str, dict]]) -> None:
        self.fsm = fsm
        self.state_attrdct = state_attrdct
        dd = dict(msg=FSMLabel._DOTOGGLE)
        for labeltxt, attrdct in state_attrdct.values():
            attrdct[STARATTR_ONCLICK] = dd
        # determine the initial state from the FSM and set it
        self.curstate = fsm.get_init_state()
        labeltxt, attrdct = state_attrdct[self.curstate]
        htmlelements.label.__init__(self, parent, idstr, attrdct, labeltxt, None)

    def enter_event(self, newevent: str) -> None:
        """Set the visible state, based on the current event.
        The new state is determined by the FSM."""
        print("fsmlabel enter event '{}'".format(newevent))
        newstate = self.fsm.get_new_state(self.curstate, newevent)
        if self.curstate != newstate:
            self._toggle_state(newstate)

    def _toggle_state(self, newstate: int) -> None:
        sattrdct = self.state_attrdct
        print("bingo newstate {}".format(newstate))
        if self.curstate != newstate and newstate in sattrdct:
            oldtxt, oldattr = sattrdct[self.curstate]
            self.curstate = newstate
            newtxt, newattr = sattrdct[self.curstate]
            self.rem_attrdct(oldattr)
            self.add_attrdct(newattr)
            self.setInnerHTML(newtxt)

    def get_current_state(self) -> int:
        """Return the current state"""
        return self.curstate

    def reset_state(self) -> None:
        self.curstate = self.fsm.get_init_state()
        self._toggle_state(self.curstate)

    def _clickfunc(self):
        """This function is called whenever the user clicks on this label.
        We use it to change our visible appearance, then pass the
        click event along as if nothing had happened...
        """
        print("TOGGLE FSMlabel CLICKFUNC")
        self.enter_event(FSMLabel.FSM_CLICK_EVENT)
        super()._clickfunc()


class ToggleFSMLabel(htmlelements.select):
    """A label whose states is controlled by an FSM.
    Each state will have alternate text and HTML attributes.

    NOTE: Our strategy to toggle the state on button click is to hijack
    the htmlelements.generic_element._clickfunc()
    """
    FSM_CLICK_EVENT = 'doclick'
    _DOTOGGLE = 'dotoggle'

    def __init__(self, parent: htmlelements.base_element,
                 idstr: str,
                 fsm: SimpleFSM,
                 state_attrdct: typing.Dict[int, typing.Tuple[str, dict]]) -> None:
        self.fsm = fsm
        self.state_attrdct = state_attrdct
        dd = dict(msg=FSMLabel._DOTOGGLE)
        for labeltxt, attrdct in state_attrdct.values():
            attrdct[STARATTR_ONCLICK] = dd
        # determine the initial state from the FSM and set it
        self.curstate = fsm.get_init_state()
        labeltxt, attrdct = state_attrdct[self.curstate]
        htmlelements.select.__init__(self, parent, idstr, attrdct, None)

    def enter_event(self, newevent: str) -> None:
        """Set the visible state, based on the current event.
        The new state is determined by the FSM."""
        print("togglefsm enter event '{}'".format(newevent))
        newstate = self.fsm.get_new_state(self.curstate, newevent)
        if self.curstate != newstate:
            self._toggle_state(newstate)

    def _toggle_state(self, newstate: int) -> None:
        sattrdct = self.state_attrdct
        print("bingo newstate {}".format(newstate))
        if self.curstate != newstate and newstate in sattrdct:
            oldtxt, oldattr = sattrdct[self.curstate]
            self.curstate = newstate
            newtxt, newattr = sattrdct[self.curstate]
            self.rem_attrdct(oldattr)
            self.add_attrdct(newattr)
            self.setInnerHTML(newtxt)

    def get_current_state(self) -> int:
        """Return the current state"""
        return self.curstate

    def reset_state(self) -> None:
        self.curstate = self.fsm.get_init_state()
        self._toggle_state(self.curstate)

    def _changefunc(self):
        """This function is called whenever the user clicks on this label.
        We use it to change our visible appearance, then pass the
        click event along as if nothing had happened...
        """
        print("TOGGLEFSM label  CHANGEFUNC")
        self.enter_event(FSMLabel.FSM_CLICK_EVENT)
        super()._changefunc()
