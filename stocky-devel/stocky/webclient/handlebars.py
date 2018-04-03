

# a small interface to the Handlebars client-side templating library
# http://handlebarsjs.com/

import typing
from org.transcrypt.stubs.browser import document, Handlebars


handycache: typing.Dict[str, typing.Any] = {}


def evalTemplate(htmlid: str, context: dict) -> str:
    """Recover a Handlebars template from the DOM by Id, then
    compile it and evaluate it with the provided context.
    The context must be a dict which defines the variables used in the Handlebars template.
    For example, if the template iterates over 'numlist' by {{#each numlist}},
    then context should be a dict such as {'numlist': [1, 2, 3]} .

    This routine returns the generated html as a string or None if something fails.
    """
    temp_func = handycache.get(htmlid, None)
    if temp_func is None:
        src_element = document.getElementById(htmlid)
        if src_element is None:
            print("handlebars: failed to find html element '{}'".format(htmlid))
            return None
        print("handlebars: compiling '{}'".format(htmlid))
        temp_func = handycache[htmlid] = Handlebars.compile(src_element.innerHTML)
        if temp_func is None:
            print("handlebars: '{}' failed to compile".format(htmlid))
            return None
    # the handlebars template is a JS function that we call with the context. It returns
    # a string containing HTML.
    return temp_func(context)
