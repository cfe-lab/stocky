"""
Created on Oct 1, 2012
@author: alendit
Version that uses pyplantuml


2018: version that calls pyplantuml

This module implements the scopyreverse Sphinx extension that produces a
UML diagram of a python module.
"""

import os

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst import Directive
from subprocess import call

try:
    from PIL import Image as IMAGE
except ImportError:
    IMAGE = None


class UMLGenerateDirective(Directive):
    """UML directive to generate a UML diagram of the classes hierarchy of a module.
    This version calls pyplantuml which I have hacked.
    (this calls a modified version of pyreverse to parse
    the python code and produce a plantuml output file. It then also (if correctly configured
    to detect the plantuml.jar) runs plantuml to produce a PNG file.
    This PNG file is returned in form of a node.image instance by the run() method for
    display by Sphinx.
    """
    required_arguments = 1
    optional_arguments = 2
    has_content = False
    DIR_NAME = "uml_images"

    def run(self):
        lverb = True
        if lverb:
            print("scopyreverse.run {}".format(self.arguments))
        env = self.state.document.settings.env
        src_dir = env.srcdir
        uml_dir = os.path.join(src_dir, self.DIR_NAME)

        if os.path.basename(uml_dir) not in os.listdir(src_dir):
            os.mkdir(uml_dir)
        env.uml_dir = uml_dir
        module_path = self.arguments[0]
        os.chdir(uml_dir)
        basename = os.path.basename(module_path).split(".")[0]
        cmd_lst = ['pyplantuml', '-o', 'png', '-p', basename,
                   os.path.abspath(os.path.join(src_dir, module_path))]
        if lverb:
            print("calling '{}'".format(" ".join(cmd_lst)))
        res = call(cmd_lst)
        if lverb:
            print("result: {}".format(res))
        if res != 0:
            print("command '{}' failed with return code: {}".format(" ".join(cmd_lst), res))
            raise RuntimeError("Failed to run pyplantuml")
        fname = os.path.join(self.DIR_NAME, "classes_{0}_classes.png".format(basename))
        if lverb:
            print("filename: '{}'\n".format(fname))
        uri = directives.uri(fname)
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
    app.add_directive('scopyreverse', UMLGenerateDirective)
