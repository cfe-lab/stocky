#!/usr/bin/env python3

"""Generate a uml file from the ChemStock sqlalchemy data definitions
for plantuml.
NOTE: this script is adapted from https://bitbucket.org/estin/sadisplay/wiki/Home
"""


import codecs
import sadisplay

import serverlib.ChemStock as cs


if __name__ == "__main__":
    desc = sadisplay.describe(
        [getattr(cs, attr) for attr in dir(cs)],
        show_methods=True,
        show_properties=True,
        show_indexes=True)

    fname = 'chemstock.plantuml'
    print("generating file '{}'..".format(fname))
    with codecs.open(fname, 'w', encoding='utf-8') as f:
        f.write(sadisplay.plantuml(desc))
