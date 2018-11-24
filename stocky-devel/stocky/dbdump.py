#!/usr/bin/env python3

"""Download the QAI database into the local DB from a chosen URL"""

# import typing
import argparse

import serverlib.qai_helper as qai_helper
import serverlib.ChemStock as ChemStock
# import serverlib.Taskmeister as Taskmeister
import serverlib.serverconfig as serverconfig


desc_str = """Load the QAI chemical stock into the local STOCKY DATABASE."""

epilog_str = """An example would be:
BLABLA
"""


def main():
    p = argparse.ArgumentParser(description=desc_str, epilog=epilog_str)
    p.add_argument("-s", "--qaiurl", help="The URL of the QAI server to poll")
    p.add_argument("-u", "--username", help="The QAI user name")
    p.add_argument("-p", "--passwd", help="The QAI user password")
    args = p.parse_args()
    lverb = True
    cfgname = 'serverconfig.yaml'
    cfg_dct = serverconfig.read_server_config(cfgname)
    print("args: {}".format(args))
    if args.qaiurl is None or args.username is None or args.passwd is None:
        raise RuntimeError('missing arguments')

    qai_sess = qai_helper.QAISession(args.qaiurl)
    qai_sess.login(args.username, args.passwd)

    locdbname = cfg_dct['LOCAL_STOCK_DB_FILE']
    print("dumping to local SQL file: {}".format(locdbname))
    csdb = ChemStock.ChemStockDB(locdbname, qai_sess, 'America/Vancouver')
    if lverb:
        print("downloading from QAI...")
    csdb.update_from_QAI()
    if lverb:
        print("OK")


if __name__ == "__main__":
    main()
