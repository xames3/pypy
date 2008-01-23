import py
import sys, os
from pypy.translator.c.test import test_newgc
from pypy.translator.translator import TranslationContext
from pypy.translator.c.genc import CStandaloneBuilder
from pypy.annotation.listdef import s_list_of_strings
from pypy import conftest


class AbstractTestAsmGCRoot:
    # the asmgcroot gc transformer doesn't generate gc_reload_possibly_moved
    # instructions:
    should_be_moving = False

    def getcompiled(self, func):
        def main(argv):
            res = func()
            print 'Result:', res
            return 0
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True)
        config.translation.gc = self.gcpolicy
        config.translation.asmgcroot = True
        t = TranslationContext(config=config)
        self.t = t
        a = t.buildannotator()
        a.build_types(main, [s_list_of_strings])
        t.buildrtyper().specialize()
        t.checkgraphs()

        cbuilder = CStandaloneBuilder(t, main, config=config)
        c_source_filename = cbuilder.generate_source(
            defines = cbuilder.DEBUG_DEFINES)
        if conftest.option.view:
            t.view()
        exe_name = cbuilder.compile()

        def run():
            lines = []
            print 'RUN: starting', exe_name
            g = os.popen("'%s'" % (exe_name,), 'r')
            for line in g:
                print 'RUN:', line.rstrip()
                lines.append(line)
            g.close()
            if not lines:
                py.test.fail("no output from subprocess")
            if not lines[-1].startswith('Result:'):
                py.test.fail("unexpected output from subprocess")
            return int(lines[-1][len('Result:'):].strip())
        return run


class TestAsmGCRootWithSemiSpaceGC(AbstractTestAsmGCRoot,
                                   test_newgc.TestSemiSpaceGC):
    pass
    # for the individual tests see
    # ====> ../../test/test_newgc.py
