""" A collection of some very basic utilities for transcrypt.
"""
# Ignore all pragma's when running CPython, since we can't control CPython's
# operation in a simple way
# def __BLApragma__(*args):
#    pass


# NOTE: we use conditional compilation here transcrypt/ CPython cases
# __pragma__('ifdef', 'sco_for_TS')
for_transcrypt = True
# __pragma__('else')
for_transcrypt = False
# __pragma__('endif')


def log(*msg):
    """A simple log routine that calls print(). This write to the web console."""
    print(*msg)

# __pragma__('ifdef', 'sco_for_TS')


if for_transcrypt:
    # 2018-09-07 does not run under 3.7.4...
    # print("bla {}".format(sorted(globals().keys())))
    # from org.transcrypt.stubs.browser import console, document
    from org.transcrypt.stubs.browser import console

    # thedocument = document

    def blalog(*msg):
        console.log(*msg)

    def nowstring() -> str:
        return 'the time is now'
else:
    def blulog(*msg):
        print(*msg)

# __pragma__('endif')
