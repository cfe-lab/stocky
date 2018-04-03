
# a collection of some very basic data structures and other useful utilities for transcrypt

# Ignore all pragma's when running CPython, since we can't control CPython's
# operation in a simple way
def __BLApragma__(*args):
    pass



# NOTE: we use conditional compilation here transcrypt/ CPython cases
# __pragma__('ifdef', 'sco_for_TS')
for_transcrypt = True
# __pragma__('else')
for_transcrypt = False
# __pragma__('endif')

# __pragma__('ifdef', 'sco_for_TS')
if for_transcrypt:
    print("bla {}".format(sorted(globals().keys())))
    from org.transcrypt.stubs.browser import console, document

    thedocument = document

    def log(*msg):
        console.log(*msg)

    def nowstring() -> str:
        return 'the time is now'
else:
    def log(*msg):
        print(*msg)

    # import datetime as dt
    #def nowstring() -> str:
    #    dd = dt.datetime.now()
    #    return dd.__str__()
        
# __pragma__('endif')


#class defaultdict(dict):
#    def __init__(self, genfunc):
#        dict.__init__(self)
#        self._genfunc = genfunc
#
#    def __getitem__(self, key):
#        if key in self:
#            return dict.__getitem__(self, key)
#        else:
#            newval = self[key] = self._genfunc()
#            return newval
#
