from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """    """

    interpleveldefs = {
        '_load_dictionary'       : 'interp_cppyy.load_dictionary',
        '_resolve_name'          : 'interp_cppyy.resolve_name',
        '_type_byname'           : 'interp_cppyy.type_byname',
        '_template_byname'       : 'interp_cppyy.template_byname',
        'CPPInstance'            : 'interp_cppyy.W_CPPInstance',
        'addressof'              : 'interp_cppyy.addressof',
        'bind_object'            : 'interp_cppyy.bind_object',
    }

    appleveldefs = {
        'gbl'                    : 'pythonify.gbl',
        'load_reflection_info'   : 'pythonify.load_reflection_info',
    }
