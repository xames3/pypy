from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib import rgc
from pypy.interpreter.argument import Arguments
from pypy.objspace.std.typeobject import W_TypeObject
from pypy.objspace.std.objectobject import W_ObjectObject
from pypy.interpreter.error import oefmt
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles, llapi
from .interp_extfunc import W_ExtensionMethod
from .interp_slot import fill_slot
from .interp_descr import add_member, add_getset
from rpython.rlib.rutf8 import surrogate_in_utf8

class W_HPyObject(W_ObjectObject):
    hpy_data = lltype.nullptr(rffi.VOIDP.TO)

    def _finalize_(self):
        w_type = self.space.type(self)
        assert isinstance(w_type, W_HPyTypeObject)
        if w_type.tp_destroy:
            w_type.tp_destroy(self.hpy_data)

    @rgc.must_be_light_finalizer
    def __del__(self):
        if self.hpy_data:
            # see the comment inside _create_instance for why this is needed
            c_obj = rffi.ptradd(self.hpy_data, llapi.SIZEOF_HPyObject_HEAD)
            lltype.free(c_obj , flavor='raw')
            self.hpy_data = lltype.nullptr(rffi.VOIDP.TO)

class W_HPyTypeObject(W_TypeObject):
    basicsize = 0
    tp_destroy = lltype.nullptr(llapi.cts.gettype('HPyFunc_destroyfunc').TO)
    
    def __init__(self, space, name, bases_w, dict_w, basicsize=0):
        # XXX: there is a discussion going on to make it possible to create
        # non-heap types with HPyType_FromSpec. Remember to fix this place
        # when it's the case.
        W_TypeObject.__init__(self, space, name, bases_w, dict_w, is_heaptype=True)
        self.basicsize = basicsize


@API.func("void *_HPy_Cast(HPyContext ctx, HPy h)")
def _HPy_Cast(space, ctx, h):
    w_obj = handles.deref(space, h)
    if not isinstance(w_obj, W_HPyObject):
        # XXX: write a test for this
        raise oefmt(space.w_TypeError, "Object of type '%T' is not a valid HPy object.", w_obj)
    return w_obj.hpy_data

@API.func("HPy _HPy_New(HPyContext ctx, HPy h_type, void **data)")
def _HPy_New(space, ctx, h_type, data):
    w_type = handles.deref(space, h_type)
    w_result = _create_instance(space, w_type)
    data = llapi.cts.cast('void**', data)
    data[0] = w_result.hpy_data
    h = handles.new(space, w_result)
    return h


@API.func("HPy HPyType_FromSpec(HPyContext ctx, HPyType_Spec *spec)")
def HPyType_FromSpec(space, ctx, spec):
    dict_w = {}
    specname = rffi.constcharp2str(spec.c_name)
    dotpos = specname.rfind('.')
    if dotpos < 0:
        name = specname
        modname = None
    else:
        name = specname[dotpos + 1:]
        modname = specname[:dotpos]

    if modname is not None:
        dict_w['__module__'] = space.newtext(modname)

    bases_w = []
    basicsize = rffi.cast(lltype.Signed, spec.c_basicsize)

    w_result = _create_new_type(
        space, space.w_type, name, bases_w, dict_w, basicsize)
    if spec.c_defines:
        add_slot_defs(space, ctx, w_result, spec.c_defines)
    return handles.new(space, w_result)

def add_slot_defs(space, ctx, w_result, c_defines):
    p = c_defines
    i = 0
    HPyDef_Kind = llapi.cts.gettype('HPyDef_Kind')
    while p[i]:
        kind = rffi.cast(lltype.Signed, p[i].c_kind)
        if kind == HPyDef_Kind.HPyDef_Kind_Slot:
            hpyslot = llapi.cts.cast('_pypy_HPyDef_as_slot*', p[i]).c_slot
            fill_slot(space, w_result, hpyslot)
        elif kind == HPyDef_Kind.HPyDef_Kind_Meth:
            hpymeth = p[i].c_meth
            name = rffi.constcharp2str(hpymeth.c_name)
            sig = rffi.cast(lltype.Signed, hpymeth.c_signature)
            w_extfunc = W_ExtensionMethod(space, name, sig, hpymeth.c_impl, w_result)
            w_result.setdictvalue(
                space, rffi.constcharp2str(hpymeth.c_name), w_extfunc)
        elif kind == HPyDef_Kind.HPyDef_Kind_Member:
            hpymember = llapi.cts.cast('_pypy_HPyDef_as_member*', p[i]).c_member
            add_member(space, w_result, hpymember)
        elif kind == HPyDef_Kind.HPyDef_Kind_GetSet:
            hpygetset = llapi.cts.cast('_pypy_HPyDef_as_getset*', p[i]).c_getset
            add_getset(space, w_result, hpygetset)
        else:
            raise oefmt(space.w_ValueError, "Unspported HPyDef.kind: %d", kind)
        i += 1

def _create_new_type(space, w_typetype, name, bases_w, dict_w, basicsize):
    pos = surrogate_in_utf8(name)
    if pos >= 0:
        raise oefmt(space.w_ValueError, "can't encode character in position "
                    "%d, surrogates not allowed", pos)
    w_type = W_HPyTypeObject(
        space, name, bases_w or [space.w_object], dict_w, basicsize)
    w_type.ready()
    return w_type

def _create_instance(space, w_type):
    assert isinstance(w_type, W_HPyTypeObject)
    w_result = space.allocate_instance(W_HPyObject, w_type)
    w_result.space = space
    basicsize = w_type.basicsize
    #
    # ad explained by the comment at the top of hpytype.h, user-defined
    # structs begin with HPyObject_HEAD to reserve some space. However, in
    # PyPy we don't need that space so we just pretend to allocate it by
    # malloc()ing LESS bytes than requested, and returning a pointer allocate
    # LESS bytes than requested, so ensure that the offsets for user-defined
    # fields are still correct.  Obviously, dereferencing the first
    # SIZEOF_HPyObject_HEAD bytes of it will be undefined behavior, but this
    # should never happen, unless the user accesses the fields called
    # "_reserved0" and "_reserved1"
    c_obj = lltype.malloc(rffi.VOIDP.TO, basicsize - llapi.SIZEOF_HPyObject_HEAD,
                          zero=True, flavor='raw')
    w_result.hpy_data = rffi.ptradd(c_obj, -llapi.SIZEOF_HPyObject_HEAD)
    if w_type.tp_destroy:
        w_result.register_finalizer(space)
    return w_result

@API.func("HPy HPyType_GenericNew(HPyContext ctx, HPy type, HPy *args, HPy_ssize_t nargs, HPy kw)")
def HPyType_GenericNew(space, ctx, h_type, args, nargs, kw):
    w_type = handles.deref(space, h_type)
    w_result = _create_instance(space, w_type)
    return handles.new(space, w_result)
