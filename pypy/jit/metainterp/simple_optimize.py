
""" Simplified optimize.py
"""
from pypy.jit.metainterp.resoperation import rop

def optimize_loop(options, old_loops, loop, cpu=None):
    if old_loops:
        return old_loops[0]
    else:
        newoperations = []
        for op in loop.operations:
            if op.opnum == rop.GUARD_NONVIRTUALIZED:
                continue
            newoperations.append(op)
        loop.operations = newoperations
        return None

def optimize_bridge(options, old_loops, loop, cpu=None):
    return old_loops[0]

class Optimizer:
    optimize_loop = staticmethod(optimize_loop)
    optimize_bridge = staticmethod(optimize_bridge)


