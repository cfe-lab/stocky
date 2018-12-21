"""Implement a pytest plugin for writing test results into a specified YAML file.
This can be read by a Sphinx plugin for documentation of test results.
"""

import pytest
import yaml


def pytest_addoption(parser):
    """Add some extra options to pytest in order to control which tests to run."""
    parser.addoption('--with_qai', action='store_true', dest="with_qai",
                     default=False, help="enable tests that access James' test version of QAI")
    parser.addoption('--with_chemstock', action='store_true', dest="with_chemstock",
                     default=False, help="enable tests that access a YAML file containing chemstock data")
    parser.addoption('--dump_chemstock', action='store_true', dest="dump_chemstock",
                     default=False, help="""Perform a test that generates a YAML-file
dump of the QAI system. This can be used in tests marked --with_chemstock.""")
    parser.addoption('--with_cs_qai', action='store_true', dest="with_cs_qai",
                     default=False, help="enable tests that update chemstock from QAI")
    # add the option for the scospec plugin
    parser.addoption(
        '--scospec', action='store', dest='scospecfile', type=str,
        help='Report test results to a YAML file in Scospec format.'
    )


def tup_from_item(item):
    node_parts = item.nodeid.split('::')
    plen = len(node_parts)
    file_name = node_parts[0]
    class_name = node_parts[1] if plen > 1 else ""
    method_name = node_parts[2] if plen > 2 else ""
    node = item.obj if hasattr(item, 'obj') else None
    docstring = node.__doc__ if node is not None else ""
    sco_tup = (file_name, class_name, method_name, docstring)
    return sco_tup


@pytest.mark.hookwrapper
def pytest_runtest_makereport(item, call):
    """In this routine, we simply attach our own information (a tuple of strings)
    to the report.
    """
    outcome = yield
    report = outcome.get_result()
    report.sco_bla = tup_from_item(item)
    # print("MAKEREP {}".format(item_str))


tst_lst = []


def pytest_runtest_logreport(report):
    """In this routine, we are passed a test report which include the result
    of the test ('outcome').
    We retrieve the extra info we had previously attached to the report, combine it
    with the outcome and append the information to tst_lst.
    This list can be written to file at session finish.
    """
    # ignore setup and teardown reporting of tests that are run.
    # keep skipped items...
    outcome = report.outcome
    if outcome != 'skipped' and report.when != "call":
        return
    # print("LOGREPORT {} --> {}".format(report.sco_bla, outcome))
    tst_lst.append(report.sco_bla + (outcome, ))


def pytest_sessionfinish(session):
    fname = pytest.config.option.scospecfile
    if fname is not None:
        print("\n**writing scospec test results to '{}'".format(fname))
        with open(fname, "w") as fo:
            fo.write(yaml.dump(tst_lst, Dumper=yaml.CDumper))
