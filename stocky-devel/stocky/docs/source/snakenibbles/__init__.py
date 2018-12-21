"""
An Sphinx extension that calles snakenibbles (show import dependency graph of python modules
using plantuml and Graphviz)
"""
import os

from docutils import nodes
import docutils.parsers.rst as rst
from subprocess import call

try:
    from PIL import Image as IMAGE
except ImportError:
    IMAGE = None

SOURCE_DIR = ":source_directory:"
EXCLUDE_STR = ":exclude:"
IN_FILES = ":infiles:"
OUT_STUB = ":outstub:"

KW_LST = [SOURCE_DIR, IN_FILES, OUT_STUB, EXCLUDE_STR]
KW_SET = frozenset(KW_LST)


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
    missing_set = KW_SET - got_set
    unknown_set = got_set - KW_SET
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


class SnakeNibblesDirective(rst.Directive):
    """A Snakenibbles directive that will draw a module import hierarchy using snakenibbles
    to produce an plantuml file. Plantuml is then envoked with this input file to produce
    a PNG file. This file, finally, will be resized using the PIL module if it is present.

    This PNG file is returned in form of a node.image instance by the run() method for
    display by Sphinx.
    """
    required_arguments = 1
    optional_arguments = 12
    has_content = False
    DIR_NAME = "uml_images"

    def run(self):
        lverb = False
        # print("SNAKENIBBLES {}".format(self.arguments))
        # NOTE: There are two 'source dirs' to consider here:
        # a) the dir of the documentation source
        # b) the source dir of the code being documented
        env = self.state.document.settings.env
        src_dir = env.srcdir
        if lverb:
            print("SNAKENIBBLES SRC_DIR {}".format(src_dir))
        argdct = getargs(self.arguments)
        if lverb:
            print("SNAKEY ARGDCT {}".format(argdct))
        uml_dir = os.path.join(src_dir, self.DIR_NAME)
        if os.path.basename(uml_dir) not in os.listdir(src_dir):
            os.mkdir(uml_dir)
        env.uml_dir = uml_dir
        # module_path = self.arguments[0]
        # os.chdir(uml_dir)
        # basename = os.path.basename(module_path).split(".")[0]
        outputstub = os.path.join(uml_dir, argdct[OUT_STUB])
        exc_dir = argdct[EXCLUDE_STR]
        infiles = argdct[IN_FILES]
        cmdlst = ['/stockysrc/scocustom/snakenibbles/snibbles.py', '-o', outputstub, '-e', exc_dir,
                  '-p', '/plantuml/plantuml.jar', '-j', '/usr/bin/java', infiles]
        if lverb:
            print("CMDLST: {}".format(cmdlst))
        code_src_dir = argdct[SOURCE_DIR]
        res = call(cmdlst, cwd=code_src_dir)
        if lverb:
            print("call res: {}".format(res))
        if res != 0:
            raise RuntimeError("return code {} for '{}'".format(" ".join(cmdlst)))
        ofilename = os.path.join(self.DIR_NAME,
                                 "{}.png".format(argdct[OUT_STUB]))
        if lverb:
            print("OFILE: {}".format(ofilename))
        uri = rst.directives.uri(ofilename)
        scale = 100
        max_width = 1000
        if IMAGE:
            i = IMAGE.open(os.path.join(src_dir, uri))
            image_width = i.size[0]
            if image_width > max_width:
                scale = max_width * scale / image_width
        img = nodes.image(uri=uri, scale=scale)
        # os.chdir(src_dir)
        return [img]


def setup(app):
    """Setup directive"""
    app.add_directive('snakenibbles', SnakeNibblesDirective)
