# add a --with_qai option to the pytest argument


def pytest_addoption(parser):
    parser.addoption('--with_qai', action='store_true', dest="with_qai",
                     default=False, help="enable tests that access James' test version of QAI")
