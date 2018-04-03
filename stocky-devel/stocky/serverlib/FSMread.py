
"""
.. module:: FSMread
    :synopsis: Implement reading of YAML files defining a finite state machine
"""


import typing
import webqai.yamlutil as yamlutil

import re
import itertools

VERSION_STR = "1.0"

# terminal symbols:
STAR = 1
LCURLY = 2
RCURLY = 3
OPERATOR = 4
IDENT = 5
COMMA = 6
ERROR = 7
END = 8


symdct = {STAR: '*',
          LCURLY: '{',
          RCURLY: '}',
          OPERATOR: 'operator (+/-)',
          IDENT: 'ident',
          COMMA: ','}


def _s_ident(scanner, token): return (IDENT, token.strip())


def _s_operator(scanner, token): return (OPERATOR, token.strip())


def _s_comma(scanner, token): return (COMMA, token.strip())


def _s_lcurl(scanner, token): return (LCURLY, token.strip())


def _s_rcurl(scanner, token): return (RCURLY, token.strip())


def _s_star(scanner, token): return (STAR, token.strip())


_setscanner = re.Scanner([
    (r"[0-9a-zA-Z_]\w*\s*", _s_ident),
    (r"\,\s*", _s_comma),
    (r"\{\s*", _s_lcurl),
    (r"\}\s*", _s_rcurl),
    (r"\*\s*", _s_star),
    (r"[\+-]\s*", _s_operator),
])


def scanstring(s: str) -> typing.Tuple[typing.List[typing.Tuple[int, str]], bool]:
    """Convert the provided string s into a list of 2-tuples.
    Each tuple has a predefined terminal symbol integer and the associated string.
    For example, (STAR, '*'), where STAR is defined above.
    An END token is appended to the end of the list upon successful parsing.
    Return the list and a Boolean := 'scanner successful'.
    """
    scan_ok = True
    retlst, retstr = _setscanner.scan(s.strip())
    if retstr:
        retlst.append((ERROR, retstr))
        scan_ok = False
    else:
        retlst.append((END, ''))
    return retlst, scan_ok


class _setter:
    """Evaluate a string containing an expression describing a subset of
    the provided baseset.
    Upon successful evaluation, the calculated set can be retrieved with getval().
    If a failure occurs, a RuntimeError is raised.

    The syntax describing the string, in EBNF, is:
    expr     :=  set { op set }.
    set      := (element | setname) .
    setname  := ( '*'  | '{' [element { ',' element } ] '}' ) .
    opname   := ('+', '-' ) .

    NOTE: There is no operator precedence, the expressions are evaulated from left to right.
    """

    def __init__(self, baseset, setstr):
        self.baseset = baseset
        tklst, scan_ok = scanstring(setstr)
        if not scan_ok:
            raise RuntimeError("set syntax error {}".format(tklst))
        self._tklst = tklst
        self._tk = 0
        self._opstack = []
        self._next()
        self.expr()

    def getval(self):
        """Return the value of expression provided in setstr """
        if len(self._opstack) == 1:
            return self._opstack[0]
        else:
            raise RuntimeError("no answer: len is %d" % len(self._opstack))

    def _next(self):
        """Get the next terminal symbol from the list"""
        self.curtk = self._tklst[self._tk]
        self._tk += 1
        return self.curtk

    def _push(self, sval):
        self._opstack.append(sval)

    def _pop(self):
        return self._opstack.pop()

    def checkexpected(self, tkexp):
        if self.curtk[0] != tkexp:
            raise RuntimeError("expected {} but got {}".format(symdct[tkexp], self.curtk[1]))

    def checkelement(self, el):
        """Make sure that el is in the baseset, i.e. is a legal element of the baseset"""
        if el not in self.baseset:
            raise RuntimeError("Illegal element name {}, base set is {}".format(el, self.baseset))

    def expr(self) -> None:
        """Parse the provided tokenized string for an expression as defined by EBNF."""
        self.set()
        while self.curtk[0] == OPERATOR:
            myop = self.curtk[1]
            self._next()
            self.set()
            # here, do the operation on the opstack
            if myop == '+':
                self._push(self._pop() | self._pop())
            elif myop == '-':
                B = self._pop()
                A = self._pop()
                self._push(A - B)
            else:
                raise RuntimeError("unknown op {}".format(myop))
        if self.curtk[0] != END:
            raise RuntimeError("EXPRESSION WITHOUT END {}".format(self.curtk))

    def set(self):
        """Parse for a set definition and push the result onto the opstack"""
        ct, cv = self.curtk
        if ct == IDENT:
            # an element in the base set
            self.checkelement(cv)
            self._push(set([cv]))
            self._next()
        elif ct == STAR:
            # the complete base set
            self._push(self.baseset)
            self._next()
        elif ct == LCURLY:
            # explicit set def
            ct, cv = self._next()
            self.checkexpected(IDENT)
            self.checkelement(cv)
            myset = set([cv])
            ct, cv = self._next()
            while ct == COMMA:
                ct, cv = self._next()
                self.checkexpected(IDENT)
                self.checkelement(cv)
                myset |= set([cv])
                ct, cv = self._next()
            # --
            self.checkexpected(RCURLY)
            self._next()
            self._push(myset)
        else:
            # shouldn't happen --don't know what to do...
            raise RuntimeError("set definition: unexpected symbol at {}".format(cv))


def readin(yamlfilename: str):
    """Read in a YAML file describing the finite state machine.
    Raise a RuntimeError exception iff there is a problem with the file.
    """
    fsm_dct = yamlutil.readyamlfile(yamlfilename)
    if not isinstance(fsm_dct, dict):
        raise RuntimeError("FSM must be a single dict class , but found a {}".format(type(fsm_dct)))
    keyset = set(fsm_dct.keys())
    needset = frozenset(['STATE', 'TRANSDEF', 'TRANSLIST', 'DOCSTRING', 'VERSION', 'NAME'])
    if not needset.issubset(keyset):
        raise RuntimeError('all of {} must be defined'.format(needset))
    # check the version string
    vstr = fsm_dct['VERSION'].strip()
    if vstr != VERSION_STR:
        raise RuntimeError("Required VERSION = {}, but got {}".format(VERSION_STR, vstr))
    # read the name
    name_str = fsm_dct['NAME'].strip()
    # all other entries must be lists -- turn them into sets which we keep in setdct
    setdct, errlst = {}, []
    for k in keyset-needset:
        lst = fsm_dct[k]
        if isinstance(lst, list):
            try:
                setdct[k] = frozenset(lst)
            except:
                errlst.append("{}: failed to create  set\n".format(k))
        else:
            errlst.append("{}: is not a list\n".format(k))
    if errlst:
        raise RuntimeError(errlst)
    setnames = frozenset(setdct.keys())
    # check 'STATE' entry
    statename = fsm_dct['STATE']
    try:
        statelst = fsm_dct[statename]
    except KeyError:
        raise RuntimeError("key error on 'STATE' index: {} not found".format(statename))
    if not isinstance(statelst, list):
        raise RuntimeError("variable defined by STATE ({}) must be a list".format(statename))
    stateset = setdct[statename]
    # check and translate TRANSDEF
    transdefstr = fsm_dct['TRANSDEF']
    if not isinstance(transdefstr, str):
        raise RuntimeError("TRANSDEF variable must be a string, but got {}".format(type(transdefstr)))
    transdeflst = [s.strip() for s in transdefstr.split(":")]
    if len(transdeflst) != 3:
        raise RuntimeError("malformed TRANSDEF string: need 3 ':'-separated entries")
    curstate, transstr, nxtstate = transdeflst
    # curstate must be equal to the STATE entry
    if curstate != statename:
        raise RuntimeError("malformed TRANSDEF string: curstate must be STATE = {}".format(statename))
    # sanity check of transstr
    ttup = [s.strip() for s in transstr.split(',')]
    transtupset = set(ttup)
    if len(ttup) != len(transtupset):
        raise RuntimeError("Double entry in transstr")
    unknown_names = transtupset - setnames
    if unknown_names:
        raise RuntimeError("unknown transtup entries {}".format(unknown_names))
    # sanity check of nxtstate
    nxttup = [s.strip() for s in nxtstate.split(',')]
    if len(nxttup) != 2:
        raise RuntimeError("Error in TRANSDEF: nxt tup must have two entries: action, newstate")
    nxttupset = set(nxttup)
    if len(nxttup) != len(nxttupset):
        raise RuntimeError("Double entry in nexttup")
    unknown_names = nxttupset - setnames
    if unknown_names:
        raise RuntimeError("unknown nexttup entries {}".format(unknown_names))
    # remember the base_set of actions for later
    action_baseset = setdct[nxttup[0]]
    # the second entry must be statename
    if statename != nxttup[1]:
        raise RuntimeError("next state must contain the same name as 'STATE' ({})".format(statename))
    leftside_len = 1 + len(transtupset)
    rightside_len = len(nxttup)
    translen = leftside_len + rightside_len
    if not isinstance(fsm_dct["TRANSLIST"], list):
        raise RuntimeError("TRANSLIST must be a list, but got a {}".format(type(fsm_dct["TRANSLIST"])))
    # convert the list of lists into a list of tuples, so that we can enter them into a set
    translst = [tuple(tl) for tl in fsm_dct["TRANSLIST"]]
    # check all entries for the correct length: must be translen
    if not all([len(tl) == translen for tl in translst]):
        raise RuntimeError("""TRANSLIST: transitions must be of length {} as defined by TRANSDEF""".format(translen))
    if len(translst) != len(set(translst)):
        check_set: typing.Set[typing.Tuple[str, ...]] = set()
        errlst = ["Detected double entries in the TRANSLIST"]
        for ttranstup in translst:
            if ttranstup in check_set:
                errlst.append("{} multiply defined".format(ttranstup))
            else:
                check_set.add(ttranstup)
        raise RuntimeError("\n".join(errlst))
    # make sure each entry is of the correct type, i.e. a subset of the prescribed baseset
    setnamestup = tuple([curstate] + list(ttup) + list(nxttup))
    reqsettup = tuple(setdct[n] for n in setnamestup)
    leftsideset: typing.Set[str] = set()
    used_actionset: typing.Set[str] = set()
    reached_states: typing.Set[str] = set()
    leaving_states: typing.Set[str] = set()
    errlst = []
    # now look at the entries of the TRANSLIST and create a jump table
    # jumptable (leftside : (action, newstate)
    jumptable = {}
    for transtup in translst:
        # all elements must be of the required baseset
        setlst = []
        for fieldstr, baseset in zip(transtup, reqsettup):
            try:
                stmp = _setter(baseset, fieldstr)
            except RuntimeError as e:
                errlst.append("{} element of wrong type in {}".format(fieldstr, transtup))
                raise RuntimeError("\n".join(errlst))
            setlst.append(stmp.getval())
        newllst, newrlst = setlst[:leftside_len], setlst[leftside_len:]
        # all left side sets must be disjoint -- first create the Cartesian product
        # of the left-hand side of this transition
        newlset = set(itertools.product(*newllst))
        if leftsideset.isdisjoint(newlset):
            leftsideset |= newlset
        else:
            overlap = leftsideset & newlset
            errlst.append("left side ({}) multiply defined in transitions ({})".format(overlap, transtup))
        # check the RHS
        # these sets may contain one element only
        if any([len(s) != 1 for s in newrlst]):
            errlst.append("right side with multiple actions or new states {}".format(transtup))
        # keep track of all actions that we actually use for checking at the end
        my_curstate_set = newllst[0]
        my_action_set, my_newstate_set = newrlst
        used_actionset |= my_action_set
        # keep track of all states we can reach and leave
        reached_states |= my_newstate_set
        leaving_states |= my_curstate_set
        # add entries into the jumptable
        rhs = (list(my_action_set)[0], list(my_newstate_set)[0])
        for lhs in newlset:
            jumptable[lhs] = rhs
    if errlst:
        raise RuntimeError("\n".join(errlst))
    # -- at this point, we have read in all the transition tuples without errors
    # do some sanity checks.
    # make sure that all possible LHS are taken care of --
    # the leftsideset must be equal to the Cartesian Product of the basesets
    left_states = set(itertools.product(*reqsettup[:leftside_len]))
    missing_left_states = left_states - leftsideset
    if missing_left_states != set():
        print("Defined {} states out of {}".format(len(leftsideset), len(left_states)))
        misstr = "\n".join(["{}".format(s) for s in missing_left_states])
        raise RuntimeError("Error: FSM has missing Left Hand Sides.\n{}".format(misstr))
    # make sure that all defined actions are used at least once
    missing_actions = action_baseset - used_actionset
    if missing_actions != set():
        print("Used only {} actions out of {} defined ones".format(len(used_actionset), len(action_baseset)))
        raise RuntimeError("Error: FSM has unused actions {}", missing_actions)
    # check state reachability
    unreachable_states = stateset - reached_states
    if unreachable_states != set():
        raise RuntimeError("Error: unreachable states found {}".format(unreachable_states))
    # check state leavability
    marooned_states = stateset - leaving_states
    if marooned_states != set():
        raise RuntimeError("Error: unleavable states found {}".format(marooned_states))
    return fsm_dct, setdct, action_baseset, stateset, setnamestup, reqsettup,\
        leftside_len, jumptable, name_str, translst
