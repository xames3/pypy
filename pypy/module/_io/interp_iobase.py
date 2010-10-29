from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.interpreter.typedef import (
    TypeDef, GetSetProperty, generic_new_descr)
from pypy.interpreter.gateway import interp2app, Arguments, unwrap_spec
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.rlib.rstring import StringBuilder

def convert_size(space, w_size):
    if space.is_w(w_size, space.w_None):
        return -1
    else:
        return space.int_w(w_size)

class W_IOBase(Wrappable):
    def __init__(self, space):
        # XXX: IOBase thinks it has to maintain its own internal state in
        # `__IOBase_closed` and call flush() by itself, but it is redundant
        # with whatever behaviour a non-trivial derived class will implement.
        self.space = space
        self.__IOBase_closed = False

    def _closed(self, space):
        # This gets the derived attribute, which is *not* __IOBase_closed
        # in most cases!
        w_closed = space.findattr(self, space.wrap('closed'))
        if w_closed is not None and space.is_true(w_closed):
            return True
        return False

    def __del__(self):
        space = self.space
        w_closed = space.findattr(self, space.wrap('closed'))
        try:
            # If `closed` doesn't exist or can't be evaluated as bool, then
            # the object is probably in an unusable state, so ignore.
            if w_closed is not None and not space.is_true(w_closed):
                space.call_method(self, "close")
        except OperationError:
            # Silencing I/O errors is bad, but printing spurious tracebacks is
            # equally as bad, and potentially more frequent (because of
            # shutdown issues).
            pass

    def _CLOSED(self):
        # Use this macro whenever you want to check the internal `closed`
        # status of the IOBase object rather than the virtual `closed`
        # attribute as returned by whatever subclass.
        return self.__IOBase_closed

    def _check_closed(self, space, message=None):
        if message is None:
            message = "I/O operation on closed file"
        if self._closed(space):
            raise OperationError(
                space.w_ValueError, space.wrap(message))

    def closed_get_w(space, self):
        return space.newbool(self.__IOBase_closed)

    @unwrap_spec('self', ObjSpace)
    def close_w(self, space):
        if self._CLOSED():
            return
        try:
            space.call_method(self, "flush")
        finally:
            self.__IOBase_closed = True

    @unwrap_spec('self', ObjSpace)
    def flush_w(self, space):
        if self._CLOSED():
            raise OperationError(
                space.w_ValueError,
                space.wrap("I/O operation on closed file"))

    @unwrap_spec('self', ObjSpace)
    def tell_w(self, space):
        return space.call_method(self, "seek", space.wrap(0), space.wrap(1))

    @unwrap_spec('self', ObjSpace)
    def enter_w(self, space):
        self._check_closed(space)
        return space.wrap(self)

    @unwrap_spec('self', ObjSpace, Arguments)
    def exit_w(self, space, __args__):
        space.call_method(self, "close")

    @unwrap_spec('self', ObjSpace)
    def iter_w(self, space):
        self._check_closed(space)
        return space.wrap(self)

    @unwrap_spec('self', ObjSpace)
    def next_w(self, space):
        w_line = space.call_method(self, "readline")
        if space.int_w(space.len(w_line)) == 0:
            raise OperationError(space.w_StopIteration, space.w_None)
        return w_line

    @unwrap_spec('self', ObjSpace)
    def isatty_w(self, space):
        return space.w_False

    @unwrap_spec('self', ObjSpace)
    def readable_w(self, space):
        return space.w_False

    @unwrap_spec('self', ObjSpace)
    def writable_w(self, space):
        return space.w_False

    @unwrap_spec('self', ObjSpace)
    def seekable_w(self, space):
        return space.w_False

    @unwrap_spec('self', ObjSpace)
    def check_readable_w(self, space):
        if not space.is_true(space.call_method(self, 'readable')):
            raise OperationError(
                space.w_IOError,
                space.wrap("file or stream is not readable"))

    @unwrap_spec('self', ObjSpace)
    def check_writable_w(self, space):
        if not space.is_true(space.call_method(self, 'writable')):
            raise OperationError(
                space.w_IOError,
                space.wrap("file or stream is not writable"))

    @unwrap_spec('self', ObjSpace)
    def check_seekable_w(self, space):
        if not space.is_true(space.call_method(self, 'seekable')):
            raise OperationError(
                space.w_IOError,
                space.wrap("file or stream is not seekable"))

    # ______________________________________________________________

    @unwrap_spec('self', ObjSpace, W_Root)
    def readline_w(self, space, w_limit=None):
        # For backwards compatibility, a (slowish) readline().
        limit = convert_size(space, w_limit)

        old_size = -1

        has_peek = space.findattr(self, space.wrap("peek"))

        builder = StringBuilder()
        size = 0

        while limit < 0 or size < limit:
            nreadahead = 1

            if has_peek:
                w_readahead = space.call_method(self, "peek", space.wrap(1))
                if not space.isinstance_w(w_readahead, space.w_str):
                    raise operationerrfmt(
                        space.w_IOError,
                        "peek() should have returned a bytes object, "
                        "not '%s'", space.type(w_readahead).getname(space, '?'))
                length = space.int_w(space.len(w_readahead))
                if length > 0:
                    n = 0
                    buf = space.str_w(w_readahead)
                    if limit >= 0:
                        while True:
                            if n >= length or n >= limit:
                                break
                            n += 1
                            if buf[n-1] == '\n':
                                break
                    else:
                        while True:
                            if n >= length:
                                break
                            n += 1
                            if buf[n-1] == '\n':
                                break
                    nreadahead = n

            w_read = space.call_method(self, "read", space.wrap(nreadahead))
            if not space.isinstance_w(w_read, space.w_str):
                raise operationerrfmt(
                    space.w_IOError,
                    "peek() should have returned a bytes object, "
                    "not '%s'", space.type(w_read).getname(space, '?'))
            read = space.str_w(w_read)
            if not read:
                break

            size += len(read)
            builder.append(read)

            if read[-1] == '\n':
                break

        return space.wrap(builder.build())

    @unwrap_spec('self', ObjSpace, W_Root)
    def readlines_w(self, space, w_hint=None):
        hint = convert_size(space, w_hint)

        if hint <= 0:
            return space.newlist(space.unpackiterable(self))

        lines_w = []
        length = 0
        while True:
            w_line = space.call_method(self, "readline")
            line_length = space.int_w(space.len(w_line))
            if line_length == 0: # done
                break

            lines_w.append(w_line)

            length += line_length
            if length > hint:
                break

        return space.newlist(lines_w)

W_IOBase.typedef = TypeDef(
    '_IOBase',
    __new__ = generic_new_descr(W_IOBase),
    __enter__ = interp2app(W_IOBase.enter_w),
    __exit__ = interp2app(W_IOBase.exit_w),
    __iter__ = interp2app(W_IOBase.iter_w),
    next = interp2app(W_IOBase.next_w),
    close = interp2app(W_IOBase.close_w),
    flush = interp2app(W_IOBase.flush_w),
    tell = interp2app(W_IOBase.tell_w),
    isatty = interp2app(W_IOBase.isatty_w),
    readable = interp2app(W_IOBase.readable_w),
    writable = interp2app(W_IOBase.writable_w),
    seekable = interp2app(W_IOBase.seekable_w),
    _checkReadable = interp2app(W_IOBase.check_readable_w),
    _checkWritable = interp2app(W_IOBase.check_writable_w),
    _checkSeekable = interp2app(W_IOBase.check_seekable_w),
    closed = GetSetProperty(W_IOBase.closed_get_w),

    readline = interp2app(W_IOBase.readline_w),
    readlines = interp2app(W_IOBase.readlines_w),
    )

class W_RawIOBase(W_IOBase):
    pass
W_RawIOBase.typedef = TypeDef(
    '_RawIOBase', W_IOBase.typedef,
    __new__ = generic_new_descr(W_RawIOBase),
    )

