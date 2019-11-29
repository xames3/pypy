from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError, oefmt
from pypy.objspace.std.listobject import W_ListObject
from pypy.module.hpy_universal.apiset import API
from pypy.module.hpy_universal import handles

@API.func("HPy HPyList_New(HPyContext ctx, HPy_ssize_t len)")
def HPyList_New(space, ctx, len):
    if len == 0:
        w_list = space.newlist([])
    else:
        w_list = space.newlist([None] * len)
    return handles.new(space, w_list)


@API.func("int HPyList_Append(HPyContext ctx, HPy h_list, HPy h_item)")
def HPyList_Append(space, ctx, h_list, h_item):
    w_list = handles.deref(space, h_list)
    # XXX the tests should check what happens in this case
    assert isinstance(w_list, W_ListObject)
    w_item = handles.deref(space, h_item)
    w_list.append(w_item)
    return rffi.cast(rffi.INT_real, 0)
