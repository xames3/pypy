from pypy.conftest import gettestobjspace
from pypy.tool.udir import udir

class AppTestIoModule:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_io'])

    def test_import(self):
        import io

    def test_iobase(self):
        import io
        io.IOBase()

        class MyFile(io.BufferedIOBase):
            def __init__(self, filename):
                pass
        MyFile("file")

    def test_openclose(self):
        import io
        with io.BufferedIOBase() as f:
            assert not f.closed
        assert f.closed

    def test_iter(self):
        import io
        class MyFile(io.IOBase):
            def __init__(self):
                self.lineno = 0
            def readline(self):
                self.lineno += 1
                if self.lineno == 1:
                    return "line1"
                elif self.lineno == 2:
                    return "line2"
                return ""

        assert list(MyFile()) == ["line1", "line2"]

    def test_exception(self):
        import _io
        e = _io.UnsupportedOperation("seek")

    def test_blockingerror(self):
        import _io
        try:
            raise _io.BlockingIOError(42, "test blocking", 123)
        except IOError, e:
            assert isinstance(e, _io.BlockingIOError)
            assert e.errno == 42
            assert e.strerror == "test blocking"
            assert e.characters_written == 123

    def test_destructor(self):
        import io
        io.IOBase()

        record = []
        class MyIO(io.IOBase):
            def __del__(self):
                record.append(1)
                super(MyIO, self).__del__()
            def close(self):
                record.append(2)
                super(MyIO, self).close()
            def flush(self):
                record.append(3)
                super(MyIO, self).flush()
        MyIO()
        import gc; gc.collect()
        assert record == [1, 2, 3]

    def test_tell(self):
        import io
        class MyIO(io.IOBase):
            def seek(self, pos, whence=0):
                return 42
        assert MyIO().tell() == 42

class AppTestOpen:
    def setup_class(cls):
        tmpfile = udir.join('tmpfile').ensure()
        cls.w_tmpfile = cls.space.wrap(str(tmpfile))

    def test_open(self):
        import io
        f = io.open(self.tmpfile, "rb")
        assert f.name.endswith('tmpfile')
        assert f.mode == 'rb'
        f.close()

    def test_open_writable(self):
        import io
        f = io.open(self.tmpfile, "w+b")
        f.close()

