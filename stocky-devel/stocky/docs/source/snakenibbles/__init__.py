"""
An Sphinx extension that calles snakenibbles
"""
import os

from docutils import nodes
from docutils.parsers.rst import directives
# SCO from sphinx.util.compat import Directive
from docutils.parsers.rst import Directive
from subprocess import call

try:
    from PIL import Image as IMAGE
except ImportError:
    IMAGE = None


KW_LST = [":source_directory:", ":infiles:", ":outfile:", ":exclude:"]
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
    return rdct


class SnakeNibblesDirective(Directive):
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
        # print("SNAKENIBBLES {}".format(self.arguments))
        env = self.state.document.settings.env
        src_dir = env.srcdir
        print("SNAKENIBBLES SRC_DIR {}".format(src_dir))
        argdct = getargs(self.arguments)
        print("SNAKEY {}".format(argdct))

        uml_dir = os.path.join(src_dir, self.DIR_NAME)
        if os.path.basename(uml_dir) not in os.listdir(src_dir):
            os.mkdir(uml_dir)
        env.uml_dir = uml_dir
        module_path = self.arguments[0]
        os.chdir(uml_dir)
        basename = os.path.basename(module_path).split(".")[0]
        # print(call(['pyreverse', '-o', 'png', '-p', basename,
        #            os.path.abspath(os.path.join(src_dir, module_path))]))
        # print(call(['pyplantuml', '-o', 'png', '-p', basename,
        #            os.path.abspath(os.path.join(src_dir, module_path))]))
        uri = directives.uri(os.path.join(self.DIR_NAME,
                                          "classes_{0}_classes.png".format(basename)))
        scale = 100
        max_width = 1000
        if IMAGE:
            i = IMAGE.open(os.path.join(src_dir, uri))
            image_width = i.size[0]
            if image_width > max_width:
                scale = max_width * scale / image_width
        img = nodes.image(uri=uri, scale=scale)
        os.chdir(src_dir)
        return [img]


def setup(app):
    """Setup directive"""
    app.add_directive('snakenibbles', SnakeNibblesDirective)
