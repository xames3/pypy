import py
import sys
from pypy.config.config import ConflictConfigError
from pypy.tool.option import make_config, make_objspace
from pypy.tool.pytest import appsupport
from pypy.conftest import option

_SPACECACHE={}
def gettestobjspace(**kwds):
    """ helper for instantiating and caching space's for testing.
    """
    try:
        config = make_config(option, **kwds)
    except ConflictConfigError as e:
        # this exception is typically only raised if a module is not available.
        # in this case the test should be skipped
        py.test.skip(str(e))
    key = config.getkey()
    try:
        return _SPACECACHE[key]
    except KeyError:
        if getattr(option, 'runappdirect', None):
            return TinyObjSpace(**kwds)
        space = maketestobjspace(config)
        _SPACECACHE[key] = space
        return space

def maketestobjspace(config=None):
    if config is None:
        config = make_config(option)
    space = make_objspace(config)
    space.startup() # Initialize all builtin modules
    space.setitem(space.builtin.w_dict, space.wrap('AssertionError'),
                  appsupport.build_pytest_assertion(space))
    space.setitem(space.builtin.w_dict, space.wrap('raises'),
                  space.wrap(appsupport.app_raises))
    space.setitem(space.builtin.w_dict, space.wrap('skip'),
                  space.wrap(appsupport.app_skip))
    space.setitem(space.builtin.w_dict, space.wrap('py3k_skip'),
                  space.wrap(appsupport.app_py3k_skip))
    space.raises_w = appsupport.raises_w.__get__(space)
    space.eq_w = appsupport.eq_w.__get__(space)
    return space


class TinyObjSpace(object):
    """An object space that delegates everything to the hosting Python."""
    def __init__(self, **kwds):
        info = getattr(sys, 'pypy_translation_info', None)
        for key, value in kwds.iteritems():
            if key == 'usemodules':
                if info is not None:
                    for modname in value:
                        if modname == 'time':
                            continue   # always either 'time' or 'rctime',
                                       # and any is fine
                        ok = info.get('objspace.usemodules.%s' % modname,
                                      False)
                        if not ok:
                            py.test.skip("cannot runappdirect test: "
                                         "module %r required" % (modname,))
                else:
                    if '__pypy__' in value:
                        py.test.skip("no module __pypy__ on top of CPython")
                continue
            if info is None:
                py.test.skip("cannot runappdirect this test on top of CPython")
            has = info.get(key, None)
            if has != value:
                #print sys.pypy_translation_info
                py.test.skip("cannot runappdirect test: space needs %s = %s, "\
                    "while pypy-c was built with %s" % (key, value, has))

        for name in ('int', 'long', 'str', 'unicode', 'None', 'ValueError',
                'OverflowError'):
            setattr(self, 'w_' + name, eval(name))
        import __builtin__ as __builtin__
        self.builtin = __builtin__

    def appexec(self, args, body):
        body = body.lstrip()
        assert body.startswith('(')
        src = py.code.Source("def anonymous" + body)
        return (src, args)

    def wrap(self, obj):
        if isinstance(obj, str):
            return obj.decode('utf-8')
        return obj

    def wrapbytes(self, obj):
        return obj

    def unpackiterable(self, itr):
        return list(itr)

    def is_true(self, obj):
        return bool(obj)

    def str_w(self, w_str):
        return w_str

    def newdict(self, module=None):
        return {}

    def newtuple(self, iterable):
        return tuple(iterable)

    def newlist(self, iterable):
        return list(iterable)

    def call_function(self, func, *args, **kwds):
        return func(*args, **kwds)

    def call_method(self, obj, name, *args, **kwds):
        return getattr(obj, name)(*args, **kwds)

    def getattr(self, obj, name):
        return getattr(obj, name)

    def setattr(self, obj, name, value):
        setattr(obj, name, value)

    def getbuiltinmodule(self, name):
        return __import__(name)

    def delslice(self, obj, *args):
        obj.__delslice__(*args)

    def is_w(self, obj1, obj2):
        return obj1 is obj2

