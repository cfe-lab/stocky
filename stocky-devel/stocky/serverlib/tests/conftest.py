# add a --with_qai option to the pytest argument


def pytest_addoption(parser):
    parser.addoption('--with_qai', action='store_true', dest="with_qai",
                     default=False, help="enable tests that access James' test version of QAI")
    parser.addoption('--with_chemstock', action='store_true', dest="with_chemstock",
                     default=False, help="enable tests that access a YAML file containing chemstock data")
    parser.addoption('--dump_chemstock', action='store_true', dest="dump_chemstock",
                     default=False, help="""Perform a test that generates a YAML-file
dump of the QAI system. This can be used in tests marked --with_chemstock.""")
    parser.addoption('--with_cs_qai', action='store_true', dest="with_cs_qai",
                     default=False, help="enable tests that update chemstock from QAI")
