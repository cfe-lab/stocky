"""Implement tables of test reports for Sphinx"""

import typing
# import os
from docutils import nodes
import docutils.parsers.rst as rst
import yaml
import yaml.scanner
import yaml.parser


RESULT_FILE = ":testresultfile:"
TST_FILE = ":testfile:"
TST_CLASS = ":testclass:"
TABLE_TITLE = ":tabletitle:"

KW_REQ_LST = [RESULT_FILE, TST_FILE]
KW_OPT_LST = [TST_CLASS, TABLE_TITLE]
KW_REQ_SET = frozenset(KW_REQ_LST)
KW_OPT_SET = frozenset(KW_OPT_LST)
KW_ALL_SET = frozenset(KW_REQ_LST + KW_OPT_LST)


def getargs(slst):
    """ We get a list fo the form
    [':source_directory:', '/stockysrc', ':infiles:', "'./*.py", "serverlib'",
       ':outfile:', 'overview.plantuml', ':exclude:', 'test']
    from which we extract the arguments for snibbles.py.
    where /stockysrc is a directory from which to run the snakenibbles.py directory.

    """
    rdct = {}
    i, N = 0, len(slst)
    while i < N:
        n = slst[i]
        i += 1
        if n.startswith(":"):
            # this is a keyword...
            rdct[n] = lst = []
            while i < N and not slst[i].startswith(':'):
                lst.append(slst[i])
                i += 1
    # check keywords for validity
    got_set = set(rdct.keys())
    missing_set = KW_REQ_SET - got_set
    unknown_set = got_set - KW_ALL_SET
    if missing_set:
        print("Missing arguments: {}".format(", ".join(missing_set)))
    if unknown_set:
        print("Unknown arguments: {}".format(", ".join(unknown_set)))
    if missing_set or unknown_set:
        print("argument string '{}'".format(slst))
        raise RuntimeError("Invalid arguments to the snakenibbles extension")
    # each value has a list of items. change this into a single string
    for k in rdct.keys():
        inlst = rdct[k]
        rdct[k] = " ".join(inlst)
    return rdct


def select_tuples(yamlfilename: str,
                  testfile: str, testclass: typing.Optional[str]) -> typing.List:
    """Select certain test result tuples from a yaml file.
    Tuples are of the form:
 !!python/tuple [serverlib/tests/test_qai_helper.py, Test_qai_helpers, test_tojson02,
  Encoding a user-defined class should work., passed]

    The results are sorted alphabetically by the test name.
    """
    try:
        with open(yamlfilename, "r") as fi:
            try:
                data = yaml.load(fi, Loader=yaml.CLoader)  # type: ignore
            except yaml.scanner.ScannerError as e:
                raise RuntimeError("YAML scanning error reading from '{}'\n{}".format(yamlfilename, e))
            except yaml.parser.ParserError as e:
                raise RuntimeError("YAML parse error reading from '{}'\n{}".format(yamlfilename, e))
    except (FileNotFoundError, IsADirectoryError):
        raise RuntimeError("YAML: file not found '{}'".format(yamlfilename))

    if not isinstance(data, list):
        raise RuntimeError("expected a list on test result file")
    # NOTE: an empty string is always in a string
    testclass = testclass or ""
    rlst = [t for t in data if (testfile in t[0] and testclass in t[1])]
    rlst.sort(key=lambda a: a[2])
    return rlst


def nice_format(instr: str) -> str:
    return " ".join(instr.split())


class PyTestDirective(rst.Directive):
    """A Sphinx directive that will load a yaml file containing test results,
    then select a subsection of these and show the test results in table form

    """
    required_arguments = 4
    optional_arguments = 16
    has_content = False

    header = ('name', 'desc', 'status')
    colwidths = (1, 2, 1)

    def run(self):
        lverb = True
        env = self.state.document.settings.env
        src_dir = env.srcdir
        if lverb:
            print("PYTESTTABLE SRC_DIR {}".format(src_dir))
        argdct = getargs(self.arguments)
        if lverb:
            print("PYTESTTABLE ARGDCT {}".format(argdct))
        test_res_file = argdct[RESULT_FILE]
        test_file = argdct[TST_FILE]
        test_class = argdct.get(TST_CLASS, None)
        tup_lst = select_tuples(test_res_file, test_file, test_class)
        if lverb:
            print("test_file: {}, testclass: {}: got {} tests".format(test_file,
                                                                      test_class,
                                                                      len(tup_lst)))
        retlst = []
        my_section = nodes.section()
        table_title = argdct.get(TABLE_TITLE, None)
        if table_title is not None:
            my_section += nodes.title(text=table_title)
        my_table = nodes.table()
        my_section += my_table

        # make the table titles...
        tgroup = nodes.tgroup(cols=len(self.header))
        my_table += tgroup
        for colwidth in self.colwidths:
            tgroup += nodes.colspec(colwidth=colwidth)
        thead = nodes.thead()
        tgroup += thead
        # head row with column titles
        thead += self.make_row(self.header)

        # table body with test results
        tbody = nodes.tbody()
        tgroup += tbody
        for t in tup_lst:
            tt = (t[2] or "", nice_format(t[3] or ""), t[4] or "")
            if lverb:
                print("ROW: {}".format(tt))
            tbody += self.make_test_row(tt)
        # --
        retlst += my_section
        if lverb:
            print('returning {}'.format(retlst))
        return retlst

    def make_row(self, txt_lst: typing.List[str]):
        row = nodes.row()
        for txt in txt_lst:
            entry = nodes.entry()
            row += entry
            entry += nodes.paragraph(text=txt)
        return row

    def make_test_row(self, txt_lst: typing.List[str]):
        """
        style classes can be one of 'passed', 'failure', 'skipped'
        """
        RES_COL = 2
        myclass = txt_lst[RES_COL] or 'failure'
        row = nodes.row(classes=[myclass])
        for nc, txt in enumerate(txt_lst):
            if nc == RES_COL:
                entry = nodes.entry(classes=[myclass])
            else:
                entry = nodes.entry()
            row += entry
            entry += nodes.paragraph(text=txt, classes=[myclass])
        return row


def setup(app):
    """Setup directive.
    See here for info on setup:
    https://shimizukawa-sphinx.readthedocs.io/en/1.3.3/extdev/tutorial.html#important-objects
    """
    app.add_stylesheet("css/common.css")
    app.add_directive('pytesttable', PyTestDirective)

    # identify the version of the extension
    return {'version': '0.1'}
