"""Define abstract base classes of how the local chemical stock database should
 behave. This interface will be implemented in one of two ways: using sqlalchemy,
and using puchdb.
"""

import typing
import hashlib
import json
import datetime

import serverlib.timelib as timelib
import serverlib.qai_helper as qai_helper


class BaseLocMutation:
    VALID_OPS = frozenset(['missing', 'found', 'moved'])


def do_hash(dat: typing.Any) -> str:
    """Calculate a hash function of a data structure.

    This routine works by converting a data structure to a json string,
    then applying the SHA1 algorithm.
    Finally, the hexdigest is returned.

    Attention:
       Because conversion to json is involved, only serialisable data structures
       can be input.
    Note:
       In this routine, crucially,  keys are sorted in dicts when converting
       to json.  This ensures that identical dicts created
       differently (adding elements in a different order)
       produce the same hash.

    Args:
       dat: A serialisable python data structure to calculate the hash of.
    Returns:
       A string representing a hash function.
    """
    return hashlib.sha1(json.dumps(dat, sort_keys=True).encode('utf-8')).hexdigest()


class LocNode:
    """An internal helper class used to sort the hierarchical location names."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.child_dct: typing.Dict[str, "LocNode"] = {}
        self.val: typing.Optional[dict] = None

    def addtree(self, dct) -> None:
        """Add a location dictionary to a leaf in the tree based on its
        hierarchical name."""
        namelst = dct['name'].split('\\')
        # print('nlst {}'.format(namelst))
        n_n = self
        for curname in namelst:
            nextlevel = n_n.child_dct.get(curname, None)
            if nextlevel is None:
                nextlevel = n_n.child_dct[curname] = LocNode(curname)
            n_n = nextlevel
        n_n.setval(dct)

    def setval(self, newval) -> None:
        """Set the value of the LocNode exactly once"""
        if self.val is None:
            self.val = newval
        else:
            raise RuntimeError('LocNode value set twice!')

    def getval(self) -> typing.Optional[dict]:
        """Return this LocNode's value"""
        return self.val

    def dfslst(self, topname, lst) -> None:
        """Perform a DFS traversal starting from this node."""
        fullname = "{}.{}".format(topname, self.name)
        val = self.getval()
        if val is not None:
            lst.append(val)
        for child in sorted(self.child_dct.values(), key=lambda a: a.name):
            child.dfslst(fullname, lst)


def sortloclist(orglst: typing.List[dict]) -> typing.List[dict]:
    """Sort the list of location dicts in a hierarchically sensible order.

    The method applied is the following: Nodes are added to a tree based on name,
    then an in-order DFS traversal is performed (children are sorted alphabetically)
    to sort the list.

    Args:
       orglst: the original, unsorted list of location dicts
    Returns:
       A copy of the input list sorted according to hierarchical location.
    """
    root = LocNode('')
    for dct in orglst:
        root.addtree(dct)
    rlst: typing.List[dict] = []
    root.dfslst("", rlst)
    return rlst


DBRecList = typing.List[typing.Dict[str, typing.Any]]

LocChangeTup = typing.Tuple[int, str]
LocChangeList = typing.List[LocChangeTup]


class BaseDB:
    """Define some common operations between databases. This includes
    how to interact with QAI via HTTP requests.
    """

    def __init__(self,
                 qaisession: typing.Optional[qai_helper.QAISession],
                 tz_name: str) -> None:
        """
        This database is accessed by the stocky web server.
        It is passed a :class:`qai_helper.QAISession` instance which it
        uses to access the QAI database via an HTTP API.
        This stock information is stored to a local file locQAIfname as an sqlite3 database
        in the server state directory if a name is provided. Otherwise it is stored in memory.

        Args:
           qaisession: the session instance used to access the QAI server.
           tz_name: the name of the local timezone.
        """
        self.qaisession = qaisession
        timelib.set_local_timezone(tz_name)
        self._current_date = timelib.loc_nowtime().date()
        self._db_has_changed = True
        self._cachedct: typing.Optional[dict] = None

    def has_changed(self) -> bool:
        """Return : the database has changed since the last time
          data for the webclient was extracted from it.
        """
        return self._db_has_changed

    def get_ts_data(self) -> qai_helper.QAIChangedct:
        """Retrieve the current timestamp data from the database.
        For each database table, we keep a timestamp indicating the last
        time it was updated. The dict of these timestamps is returned.
        """
        raise NotImplementedError("not implemented")

    def update_from_qai(self) -> dict:
        """Update the local ChemStock database using the qaisession.
           Returns:
              A dict describing what happened (success, error messages)
        """
        qaisession = self.qaisession
        if qaisession is None or not qaisession.is_logged_in():
            return dict(ok=False, msg="User not logged in")
        # get the locally stored timestamp data from our database
        cur_tsdata = self.get_ts_data()
        try:
            newds = qai_helper.QAIDataset(None, cur_tsdata)
        except RuntimeError as err:
            return dict(ok=False, msg="QAI access error: {}".format(str(err)))
        # load those parts from QAI that are out of date
        update_dct = qaisession.clever_update_qai_dump(newds)
        # if any value is True, then we did get something from QAI...
        num_updated = sum(update_dct.values())
        if num_updated > 0:
            try:
                self._db_has_changed = self.load_qai_data(newds, update_dct)
            except TypeError as err:
                return dict(ok=False, msg="database error: {}".format(str(err)))
        return dict(ok=True, msg="Successfully updated {} tables for QAI".format(num_updated))

    def load_qai_data(self,
                      qai_ds: qai_helper.QAIDataset,
                      update_dct: typing.Optional[qai_helper.QAIUpdatedct] = None) -> bool:
        """Replace the complete database contents with the data contained in qai_ds.
        If update_dct is provided, only update those tables for which
        update_dct[idname] is True.

        Args:
           qai_ds: the dataset provided by from QAI.
           update_dct: indicate those tables that need updating.
        Returns:
           'the update was successful'.
        """
        raise NotImplementedError('override this in subclasses')

    def calc_final_state(self, slst: typing.List[dict]) -> typing.Tuple[dict, bool, bool]:
        """ Calculate the final state from this list of states.
        We return the nominal state record and two booleans:
        ismissing, hasexpired.

        Strategy: we assign values to the various possible states and sort according
        to these values.
        Any missing record will be the first one.
        The exp record is the last one (should exist, check the date with current date)
        The nominal state is the second to last in the list.
        """
        if len(slst) < 2:
            # raise RuntimeError("state list is too short {}".format(slst))
            # the list may also contain a single EXPIRED record
            # or, in legacy cases, a single IN_USE record.
            nom_state = exp_dict = slst[0]
            ismissing = False
            # if exp_dict['status'] != 'EXPIRED':
            #    raise RuntimeError('exp_dict is not expired {}'.format(exp_dict))
        else:
            odct = dict(MISSING=-1, MADE=0, VALIDATED=1, IN_USE=2,
                        USED_UP=5, EXPIRED=6, RUO_EXPIRED=7, DISPOSED=8)
            # create tuples of input dicts with scores from odct.
            try:
                plst = [(d, odct.get(d['status'], None)) for d in slst]
            except KeyError:
                raise RuntimeError("status field missing in state record {}".format(slst))
            qlst = [tt for tt in plst if tt[1] is not None]
            qlst.sort(key=lambda a: a[1])
            exp_dict = qlst[-1][0]
            nom_state = qlst[-2][0]
            ismissing = qlst[0][0]['status'] == 'MISSING'
        # we could have no expired record, but a used up record instead.
        exp_state = exp_dict.get('status', None)
        if exp_state is None:
            raise RuntimeError("status field missing in state record {}".format(exp_dict))
        elif exp_state == 'EXPIRED':
            # Cannot use fromisoformat in 3.6...
            # expiry_date = datetime.date.fromisoformat(exp_dict['occurred'])
            # the string is of the form '2011-04-20'
            expiry_date = datetime.date(*[int(s) for s in exp_dict['occurred'].split('-')])
            has_expired = expiry_date < self._current_date
        else:
            has_expired = False
        # print("FFF {}".format(slst))
        rtup = (nom_state, ismissing, has_expired)
        # print("GGG {}".format(rtup))
        return rtup

    def get_location_list(self) -> DBRecList:
        """Return a list of all defined locations."""
        raise NotImplementedError('not implemented')

    def get_reagent_item_list(self) -> DBRecList:
        """Return a list of all reagent items."""
        raise NotImplementedError('not implemented')

    def get_reagent_item_status_list(self) -> DBRecList:
        """Return a list of all reagent item statuses."""
        raise NotImplementedError('not implemented')

    def get_reagent_list(self) -> DBRecList:
        """Return a list of all reagents."""
        raise NotImplementedError('not implemented')

    def _do_generate_webclient_stocklist(self) -> dict:
        """Generate the stock list in a form required by the web client.

        Returns:
        The dict returned has the following entries:
        loclst: a list of dicts containing the stock locations, e.g.

           [{'id': 10000, 'name': 'SPH'}, {'id': 10001, 'name': 'SPH\\638'}, ... ]

        The itemlst is a list of dicts containing:

         {'id': 18478, 'last_seen': None, 'lot_num': '2019AD3EB',
            'notes': '8 bottles of spare reagents',
            'qcs_location_id': 10010,
            'qcs_reag_id': 6297, 'rfid': 'REPLACE ME'},
         {'id': 18479, 'last_seen': None, 'lot_num': 'INT.BP.17.02',
            'notes': None, 'qcs_location_id': 10016,
            'qcs_reag_id': 6217, 'rfid': 'REPLACE ME'}

        The itmstatlst is a list of dicts containing:

          {'id': 41418, 'occurred': '2021-04-30T07:00:00Z',
            'qcs_reag_item_id': 18512, 'qcs_user_id': 113, 'status': 'EXPIRED'},
          {'id': 41419, 'occurred': '2018-06-01T22:54:26Z',
            'qcs_reag_item_id': 18513, 'qcs_user_id': 112, 'status': 'MADE'},
          {'id': 41420, 'occurred': '2020-04-03T00:00:00Z',
            'qcs_reag_item_id': 18513, 'qcs_user_id': 112, 'status': 'EXPIRED'}

        The reagentlst is a list of dicts containing:

          {'id': 8912, 'name': 'Atazanavir-bisulfate', 'basetype': 'reagent',
            'catalog_number': None, 'category': 'TDM', 'date_msds_expires': None,
            'disposed': None, 'expiry_time': None,
            'hazards': 'Avoid inhalation, skin and eye contact. Wear PPE.',
            'location': None, 'msds_filename': 'ATV_BS_A790050MSDS.pdf',
            'needs_validation': None, 'notes': None, 'qcs_document_id': None,
            'storage': '-20 C', 'supplier': None},
          {'id': 8932, 'name': 'Triton X-100', 'basetype': 'stockchem',
            'catalog_number': 'T8787', 'category': 'Other Chemicals',
            'date_msds_expires': '2020-02-28T00:00:00Z', 'disposed': None,
            'expiry_time': 2555, 'hazards': None, 'location': None,
            'msds_filename': None, 'needs_validation': None,
            'notes': None, 'qcs_document_id': None, 'storage': 'Room Temperature',
            'supplier': 'Sigma Aldrich'},
         {'id': 8952, 'name': 'Proviral V3 Primary 1st PCR  mix', 'basetype': 'reagent',
            'catalog_number': None, 'category': 'PCR',
            'date_msds_expires': None, 'disposed': None,
            'expiry_time': None, 'hazards': None,
            'location': '604', 'msds_filename': None,
            'needs_validation': None,
            'notes': None, 'qcs_document_id': None,
            'storage': '-20 C', 'supplier': None}
        """
        # NOTE: as we want dicts and not Location instances, we go directly to
        # the 'SQL level' (session.execute() and not the 'ORM level' (session.query())
        # of sqlquery.
        loclst = self.get_location_list()
        itmlst = self.get_reagent_item_list()
        itmstat = self.get_reagent_item_status_list()

        # create a Dict[locationid, List[reagentitem]] and a Dict[RFID, reagentitem]
        d_d: typing.Dict[typing.Optional[int], typing.List[dict]] = {}
        # rfid_reagitem_dct = ff = {}
        f_f: typing.Dict[str, dict] = {}
        for reag_item in itmlst:
            loc_id = reag_item.get('qcs_location_id', None)
            # we will keep a list of items with None locations... should not happen, but does
            # then we add these to the UNKNOWN list later on
            d_d.setdefault(loc_id, []).append(reag_item)
            # if loc_id is not None:
            # else:
            #    raise RuntimeError("found None location {}".format(reag_item))
            #
            rfidstr = reag_item.get('rfid', None)
            if rfidstr is not None:
                if rfidstr != 'REPLACE ME':
                    f_f.setdefault(rfidstr, reag_item)
            else:
                raise RuntimeError("found None location {}".format(reag_item))
        # unmangling for None...
        # find loc_id for 'UNKNOWN'...
        if None in d_d:
            none_lst = d_d[None]
            del d_d[None]
            flst = [loc for loc in loclst if loc['name'] == 'UNKNOWN']
            assert len(flst) == 1, "cannot determine 'UNKNOWN' location"
            unknown_lst = d_d.setdefault(flst[0]['id'], [])
            unknown_lst.extend(none_lst)
        #
        # NOW, create a Dict[locationid, Tuple[locrecord, List[reagentitem]]]
        # which we send to the client
        r_r: typing.Dict[int, typing.Tuple[dict, typing.List[dict]]] = {}
        locid_reagitem_dct = r_r
        for location in loclst:
            loc_id = location.get('id', None)
            r_r[loc_id] = (location, d_d.get(loc_id, []))
        assert len(r_r) == len(loclst), "problem with location ids!"
        #
        # collect the state records for each reagent item...
        z_z: typing.Dict[int, list] = {}
        for state in itmstat:
            reag_item_id = state['qcs_reag_item_id']
            # we want to replace the occurred timedate entry with a simple date
            # to present to the user, i.e.
            # 'occurred': '2011-04-20T00:00:00Z'  -> '2011-04-20'
            dstr = state['occurred']
            state['occurred'] = dstr.split('T')[0]
            z_z.setdefault(reag_item_id, []).append(state)
        # and evaluate the 'final state' for each reagent item
        ritemdct = {}
        for reag_item in itmlst:
            reag_item_id = reag_item['id']
            state_lst = z_z.get(reag_item_id, None)
            if state_lst is None:
                state_info = None
            else:
                state_info = self.calc_final_state(state_lst)
                # print("BLAAA {} {}".format(reag_item_id, state_info))
                # we eliminate any reagent item that has a state of 'USED_UP'.
                dct, ismissing, hasexpired = state_info
                state_info = None if dct['status'] == 'USED_UP' else state_info
            if state_info is not None:
                ritemdct[reag_item_id] = (reag_item, state_info)
            # else:
            # print("skipping {}".format(reag_item))
        # create a Dict[reagentid, reagent]
        rl = self.get_reagent_list()
        rg = {}
        for reagent in rl:
            # delete the legacy location field in reagents...
            reagent.pop('location', None)
            reagent_id = reagent.get('id', None)
            if reagent_id is not None:
                rg[reagent_id] = reagent
            else:
                raise RuntimeError("reagent ID is None")
        assert len(rg) == len(rl), "problem with reagent ids!"
        # "itmstatlst": itmstat,
        # finally, sort the loclst according to a hierarchy
        loclst = sortloclist(loclst)
        # , "rfiddct": rfid_reagitem_dct}
        return {"loclst": loclst, "locdct": locid_reagitem_dct,
                "ritemdct": ritemdct, "reagentdct": rg}

    def generate_webclient_stocklist(self) -> dict:
        """Generate the chemical stock list in a form suitable for the webclient.

        Returns:
           The dict of stock items for the webclient.

        Raises:
           RuntimeError: if the update from QAI failed.
        """
        if self._db_has_changed:
            self._cachedct = self._do_generate_webclient_stocklist()
            self._db_has_changed = False
        if self._cachedct is None:
            raise RuntimeError('Internal error')
        return self._cachedct

    # location changes ---
    def reset_loc_changes(self) -> None:
        """Remove all location changes in the database.
        A location change occurs when, during stock taking, a reagent item was
        found in a location that does not agree with the database.
        The user enters a location change for that item to be uploaded
        to QAI at a later date.
        """
        raise NotImplementedError('not implemented')

    def number_of_loc_changes(self) -> int:
        """Return the number of location changes currently in the database"""
        raise NotImplementedError('not implemented')

    def _verify_loc_changes(self, locid: int, locdat: LocChangeList) -> None:
        """Perform a sanity check on the location changes.

        This routine should be called in add_loc_changes() before any changes
        are actually committed to the database."""
        # NOTE: type check all records before adding any records. In this way,
        # any type exception does no change the database.
        if not isinstance(locid, int):
            raise ValueError("locid must be an int")
        print("ADDLOCCHANGES : {}".format(locdat))
        for reag_itm_id, opstring in locdat:
            if not isinstance(reag_itm_id, int):
                raise ValueError("reag_itm_id must be an int")
            if not isinstance(opstring, str):
                raise ValueError("opstring must be a string")
            if opstring not in BaseLocMutation.VALID_OPS:
                raise ValueError("unknown opstring '{}', valid ops: {}".format(opstring,
                                                                               BaseLocMutation.VALID_OPS))

    def add_loc_changes(self, locid: int, locdat: LocChangeList) -> None:
        """Add a location change to the database.

        Any location mutation with an existing reagent_item id will be silently overwritten
        by any location id, and opstring. In addition, do_ignore will be set to False.

        Args:
           locid: the id of the new location of the reagent items in locdat
           locdat: a list of tuple with an reagent_item id (int) and an opstring (str)
           indicating the items to change the location of.
              (reagent item ID, string)
              For example: (18023, 'missing')
        Raises:
           ValueError: if the data types are not as expected.
        """
        raise NotImplementedError('not implemented')

    def set_ignore_flag(self, reag_item_id: int, do_ignore: bool) -> dict:
        """Set/reset the ignore location change flag.

        Args:
           reag_item_id: the reagent item with a location change
           do_ignore: set this to True (the location change is ignored) or False
        Returns:
           A dict with a response that can be sent back to the webclient for diagnostics.
           The dict will have an 'ok' boolean entry, and a 'msg' string entry.
        """
        raise NotImplementedError('not implemented')

    def get_loc_changes(self, oldhash: typing.Optional[str] = None) -> \
            typing.Tuple[str, typing.Optional[typing.Dict[int, LocChangeList]]]:
        """Return all location changes in the database.

        Args:
           oldhash: an optional hashkey indicating the last retrieved database state.
        Returns:
           If oldhash does not match our current hash,
           return the new hash and a new dictionary.
           The dictionary keys are location id's, and the values are a list of tuples.
           The tuples are of the form (reagent item id, operation string,
                                       row id, row ignore boolean)
           If the hash does match, return the newhash and None. In this case, the stocky server
           will know that the webclient already has an a up-to-date version of the location changes.
        """
        raise NotImplementedError('not implemented')

    def perform_loc_changes(self, move_dct: dict) -> dict:
        """
         * Report the required changes from the list provided to QAI.
         * Update the local Locmutation table accordingly
         * Purge successfully recorded locmutations
         * Replenish our DB from QAI.
         * Return a dict in response (success/failure)
        """
        raise NotImplementedError('not implemented')
