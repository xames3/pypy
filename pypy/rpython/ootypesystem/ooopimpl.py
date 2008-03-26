from pypy.rpython.ootypesystem import ootype

# ____________________________________________________________
# Implementation of the 'canfold' oo operations


def op_ooupcast(INST, inst):
    return ootype.ooupcast(INST, inst)
op_ooupcast.need_result_type = True

def op_oodowncast(INST, inst):
    return ootype.oodowncast(INST, inst)
op_oodowncast.need_result_type = True

def op_oononnull(inst):
    checkinst(inst)
    return bool(inst)

def op_ooisnull(inst):
    checkinst(inst)
    return not bool(inst)

def op_oois(obj1, obj2):
    if is_inst(obj1):
        checkinst(obj2)
        return obj1 == obj2   # NB. differently-typed NULLs must be equal
    elif isinstance(obj1, ootype._class):
        assert isinstance(obj2, ootype._class)
        return obj1 is obj2
    else:
        assert False, "oois on something silly"

def op_instanceof(inst, INST):
    return ootype.instanceof(inst, INST)

def op_classof(inst):
    return ootype.classof(inst)

def op_subclassof(class1, class2):
    return ootype.subclassof(class1, class2)


def is_inst(inst):
    return isinstance(ootype.typeOf(inst), (ootype.Instance, ootype.BuiltinType, ootype.StaticMethod))

def checkinst(inst):
    assert is_inst(inst)

# ____________________________________________________________

def get_op_impl(opname):
    # get the op_xxx() function from the globals above
    return globals()['op_' + opname]
