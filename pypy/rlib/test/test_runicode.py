import py
import sys, random
from pypy.rlib import runicode

def test_unichr():
    a = runicode.UNICHR(0xffff)
    assert a == u'\uffff'
    if runicode.MAXUNICODE > 0xffff:
        a = runicode.UNICHR(0x10000)
        if sys.maxunicode < 0x10000:
            assert len(a) == 2      # surrogates
        else:
            assert len(a) == 1
    else:
        py.test.raises(ValueError, runicode.UNICHR, 0x10000)


class UnicodeTests(object):
    def typeequals(self, x, y):
        assert x == y
        assert type(x) is type(y)

    def getdecoder(self, encoding):
        return getattr(runicode, "str_decode_%s" % encoding.replace("-", "_"))

    def getencoder(self, encoding):
        return getattr(runicode,
                       "unicode_encode_%s" % encoding.replace("-", "_"))

    def checkdecode(self, s, encoding):
        decoder = self.getdecoder(encoding)
        if isinstance(s, str):
            trueresult = s.decode(encoding)
        else:
            trueresult = s
            s = s.encode(encoding)
        result, consumed = decoder(s, len(s), True)
        assert consumed == len(s)
        self.typeequals(trueresult, result)

    def checkencode(self, s, encoding):
        encoder = self.getencoder(encoding)
        if isinstance(s, unicode):
            trueresult = s.encode(encoding)
        else:
            trueresult = s
            s = s.decode(encoding)
        result = encoder(s, len(s), True)
        self.typeequals(trueresult, result)

    def checkencodeerror(self, s, encoding, start, stop):
        called = [False]
        def errorhandler(errors, enc, msg, t, startingpos,
                         endingpos):
            called[0] = True
            assert errors == "foo!"
            assert enc == encoding
            assert t is s
            assert start == startingpos
            assert stop == endingpos
            return "42424242", stop
        encoder = self.getencoder(encoding)
        result = encoder(s, len(s), "foo!", errorhandler)
        assert called[0]
        assert "42424242" in result

    def checkdecodeerror(self, s, encoding, start, stop, addstuff=True):
        called = [0]
        def errorhandler(errors, enc, msg, t, startingpos,
                         endingpos):
            called[0] += 1
            if called[0] == 1:
                assert errors == "foo!"
                assert enc == encoding
                assert t is s
                assert start == startingpos
                assert stop == endingpos
                return u"42424242", stop
            return u"", endingpos
        decoder = self.getdecoder(encoding)
        if addstuff:
            s += "some rest in ascii"
        result, _ = decoder(s, len(s), "foo!", True, errorhandler)
        assert called[0] > 0
        assert "42424242" in result
        if addstuff:
            assert result.endswith(u"some rest in ascii")


class TestDecoding(UnicodeTests):
    
    # XXX test bom recognition in utf-16
    # XXX test proper error handling

    def test_all_ascii(self):
        for i in range(128):
            for encoding in "utf-8 latin-1 ascii".split():
                self.checkdecode(chr(i), encoding)

    def test_all_first_256(self):
        for i in range(256):
            for encoding in ("utf-7 utf-8 latin-1 utf-16 utf-16-be utf-16-le "
                             "utf-32 utf-32-be utf-32-le").split():
                self.checkdecode(unichr(i), encoding)

    def test_first_10000(self):
        for i in range(10000):
            for encoding in ("utf-7 utf-8 utf-16 utf-16-be utf-16-le "
                             "utf-32 utf-32-be utf-32-le").split():
                self.checkdecode(unichr(i), encoding)

    def test_random(self):
        for i in range(10000):
            v = random.randrange(sys.maxunicode)
            if 0xd800 <= v <= 0xdfff:
                continue
            uni = unichr(v)
            if sys.version >= "2.7":
                self.checkdecode(uni, "utf-7")
            for encoding in ("utf-8 utf-16 utf-16-be utf-16-le "
                             "utf-32 utf-32-be utf-32-le").split():
                self.checkdecode(uni, encoding)

    def test_maxunicode(self):
        uni = unichr(sys.maxunicode)
        if sys.version >= "2.7":
            self.checkdecode(uni, "utf-7")
        for encoding in ("utf-8 utf-16 utf-16-be utf-16-le "
                         "utf-32 utf-32-be utf-32-le").split():
            self.checkdecode(uni, encoding)

    def test_single_chars_utf8(self):
        for s in ["\xd7\x90", "\xd6\x96", "\xeb\x96\x95", "\xf0\x90\x91\x93"]:
            self.checkdecode(s, "utf-8")

    def test_utf8_errors(self):
        for s in [# unexpected end of data
                  "\xd7", "\xd6", "\xeb\x96", "\xf0\x90\x91"]:
            self.checkdecodeerror(s, "utf-8", 0, len(s), addstuff=False)

        # unexpected code byte
        for s in ["\x81", "\xbf"]:
            self.checkdecodeerror(s, "utf-8", 0, 1, addstuff=True)

        # invalid data 2 byte
        for s in ["\xd7\x50", "\xd6\x06", "\xd6\xD6"]:
            self.checkdecodeerror(s, "utf-8", 0, 1, addstuff=True)
        # invalid data 3 byte
        for s in ["\xeb\x56\x95", "\xeb\x06\x95", "\xeb\xD6\x95"]:
            self.checkdecodeerror(s, "utf-8", 0, 1, addstuff=True)
        for s in ["\xeb\x96\x55", "\xeb\x96\x05", "\xeb\x96\xD5"]:
            self.checkdecodeerror(s, "utf-8", 0, 2, addstuff=True)
        # invalid data 4 byte
        for s in ["\xf0\x50\x91\x93", "\xf0\x00\x91\x93", "\xf0\xd0\x91\x93"]:
            self.checkdecodeerror(s, "utf-8", 0, 1, addstuff=True)
        for s in ["\xf0\x90\x51\x93", "\xf0\x90\x01\x93", "\xf0\x90\xd1\x93"]:
            self.checkdecodeerror(s, "utf-8", 0, 2, addstuff=True)
        for s in ["\xf0\x90\x91\x53", "\xf0\x90\x91\x03", "\xf0\x90\x91\xd3"]:
            self.checkdecodeerror(s, "utf-8", 0, 3, addstuff=True)


    def test_issue8271(self):
        # From CPython
        # Issue #8271: during the decoding of an invalid UTF-8 byte sequence,
        # only the start byte and the continuation byte(s) are now considered
        # invalid, instead of the number of bytes specified by the start byte.
        # See http://www.unicode.org/versions/Unicode5.2.0/ch03.pdf (page 95,
        # table 3-8, Row 2) for more information about the algorithm used.
        FFFD = u'\ufffd'
        sequences = [
            # invalid start bytes
            ('\x80', FFFD), # continuation byte
            ('\x80\x80', FFFD*2), # 2 continuation bytes
            ('\xc0', FFFD),
            ('\xc0\xc0', FFFD*2),
            ('\xc1', FFFD),
            ('\xc1\xc0', FFFD*2),
            ('\xc0\xc1', FFFD*2),
            # with start byte of a 2-byte sequence
            ('\xc2', FFFD), # only the start byte
            ('\xc2\xc2', FFFD*2), # 2 start bytes
            ('\xc2\xc2\xc2', FFFD*3), # 2 start bytes
            ('\xc2\x41', FFFD+'A'), # invalid continuation byte
            # with start byte of a 3-byte sequence
            ('\xe1', FFFD), # only the start byte
            ('\xe1\xe1', FFFD*2), # 2 start bytes
            ('\xe1\xe1\xe1', FFFD*3), # 3 start bytes
            ('\xe1\xe1\xe1\xe1', FFFD*4), # 4 start bytes
            ('\xe1\x80', FFFD), # only 1 continuation byte
            ('\xe1\x41', FFFD+'A'), # invalid continuation byte
            ('\xe1\x41\x80', FFFD+'A'+FFFD), # invalid cb followed by valid cb
            ('\xe1\x41\x41', FFFD+'AA'), # 2 invalid continuation bytes
            ('\xe1\x80\x41', FFFD+'A'), # only 1 valid continuation byte
            ('\xe1\x80\xe1\x41', FFFD*2+'A'), # 1 valid and the other invalid
            ('\xe1\x41\xe1\x80', FFFD+'A'+FFFD), # 1 invalid and the other valid
            # with start byte of a 4-byte sequence
            ('\xf1', FFFD), # only the start byte
            ('\xf1\xf1', FFFD*2), # 2 start bytes
            ('\xf1\xf1\xf1', FFFD*3), # 3 start bytes
            ('\xf1\xf1\xf1\xf1', FFFD*4), # 4 start bytes
            ('\xf1\xf1\xf1\xf1\xf1', FFFD*5), # 5 start bytes
            ('\xf1\x80', FFFD), # only 1 continuation bytes
            ('\xf1\x80\x80', FFFD), # only 2 continuation bytes
            ('\xf1\x80\x41', FFFD+'A'), # 1 valid cb and 1 invalid
            ('\xf1\x80\x41\x41', FFFD+'AA'), # 1 valid cb and 1 invalid
            ('\xf1\x80\x80\x41', FFFD+'A'), # 2 valid cb and 1 invalid
            ('\xf1\x41\x80', FFFD+'A'+FFFD), # 1 invalid cv and 1 valid
            ('\xf1\x41\x80\x80', FFFD+'A'+FFFD*2), # 1 invalid cb and 2 invalid
            ('\xf1\x41\x80\x41', FFFD+'A'+FFFD+'A'), # 2 invalid cb and 1 invalid
            ('\xf1\x41\x41\x80', FFFD+'AA'+FFFD), # 1 valid cb and 1 invalid
            ('\xf1\x41\xf1\x80', FFFD+'A'+FFFD),
            ('\xf1\x41\x80\xf1', FFFD+'A'+FFFD*2),
            ('\xf1\xf1\x80\x41', FFFD*2+'A'),
            ('\xf1\x41\xf1\xf1', FFFD+'A'+FFFD*2),
            # with invalid start byte of a 4-byte sequence (rfc2279)
            ('\xf5', FFFD), # only the start byte
            ('\xf5\xf5', FFFD*2), # 2 start bytes
            ('\xf5\x80', FFFD*2), # only 1 continuation byte
            ('\xf5\x80\x80', FFFD*3), # only 2 continuation byte
            ('\xf5\x80\x80\x80', FFFD*4), # 3 continuation bytes
            ('\xf5\x80\x41', FFFD*2+'A'), #  1 valid cb and 1 invalid
            ('\xf5\x80\x41\xf5', FFFD*2+'A'+FFFD),
            ('\xf5\x41\x80\x80\x41', FFFD+'A'+FFFD*2+'A'),
            # with invalid start byte of a 5-byte sequence (rfc2279)
            ('\xf8', FFFD), # only the start byte
            ('\xf8\xf8', FFFD*2), # 2 start bytes
            ('\xf8\x80', FFFD*2), # only one continuation byte
            ('\xf8\x80\x41', FFFD*2 + 'A'), # 1 valid cb and 1 invalid
            ('\xf8\x80\x80\x80\x80', FFFD*5), # invalid 5 bytes seq with 5 bytes
            # with invalid start byte of a 6-byte sequence (rfc2279)
            ('\xfc', FFFD), # only the start byte
            ('\xfc\xfc', FFFD*2), # 2 start bytes
            ('\xfc\x80\x80', FFFD*3), # only 2 continuation bytes
            ('\xfc\x80\x80\x80\x80\x80', FFFD*6), # 6 continuation bytes
            # invalid start byte
            ('\xfe', FFFD),
            ('\xfe\x80\x80', FFFD*3),
            # other sequences
            ('\xf1\x80\x41\x42\x43', u'\ufffd\x41\x42\x43'),
            ('\xf1\x80\xff\x42\x43', u'\ufffd\ufffd\x42\x43'),
            ('\xf1\x80\xc2\x81\x43', u'\ufffd\x81\x43'),
            ('\x61\xF1\x80\x80\xE1\x80\xC2\x62\x80\x63\x80\xBF\x64',
             u'\x61\uFFFD\uFFFD\uFFFD\x62\uFFFD\x63\uFFFD\uFFFD\x64'),
        ]
        def replace_handler(errors, codec, message, input, start, end):
            return FFFD, end
        def ignore_handler(errors, codec, message, input, start, end):
            return u'', end
        for n, (seq, res) in enumerate(sequences):
            decoder = self.getdecoder('utf-8')
            raises(UnicodeDecodeError, decoder, seq, len(seq), None, final=True)
            assert decoder(seq, len(seq), None, final=True,
                           errorhandler=replace_handler) == (res, len(seq))
            assert decoder(seq + 'b', len(seq) + 1, None, final=True,
                           errorhandler=replace_handler) == (res + u'b',
                                                             len(seq) + 1)
            res = res.replace(FFFD, u'')
            assert decoder(seq, len(seq), None, final=True,
                           errorhandler=ignore_handler) == (res, len(seq))

    def test_ascii_error(self):
        self.checkdecodeerror("abc\xFF\xFF\xFFcde", "ascii", 3, 4)

    def test_utf16_errors(self):
        # trunkated BOM
        for s in ["\xff", "\xfe"]:
            self.checkdecodeerror(s, "utf-16", 0, len(s), addstuff=False)

        for s in [
                  # unexpected end of data ascii
                  "\xff\xfeF",
                  # unexpected end of data
                  '\xff\xfe\xc0\xdb\x00', '\xff\xfe\xc0\xdb', '\xff\xfe\xc0', 
                  ]:
            self.checkdecodeerror(s, "utf-16", 2, len(s), addstuff=False)
        for s in [
                  # illegal surrogate
                  "\xff\xfe\xff\xdb\xff\xff",
                  ]:
            self.checkdecodeerror(s, "utf-16", 2, 4, addstuff=False)

    def test_utf16_bugs(self):
        s = '\x80-\xe9\xdeL\xa3\x9b'
        py.test.raises(UnicodeDecodeError, runicode.str_decode_utf_16_le,
                       s, len(s), True)

    def test_utf7_bugs(self):
        u = u'A\u2262\u0391.'
        assert runicode.unicode_encode_utf_7(u, len(u), None) == 'A+ImIDkQ.'

    def test_utf7_partial(self):
        s = u"a+-b".encode('utf-7')
        assert s == "a+--b"
        decode = self.getdecoder('utf-7')
        assert decode(s, 1, None) == (u'a', 1)
        assert decode(s, 2, None) == (u'a', 1)
        assert decode(s, 3, None) == (u'a+', 3)
        assert decode(s, 4, None) == (u'a+-', 4)
        assert decode(s, 5, None) == (u'a+-b', 5)

    def test_utf7_surrogates(self):
        encode = self.getencoder('utf-7')
        u = u'\U000abcde'
        assert encode(u, len(u), None) == '+2m/c3g-'
        decode = self.getdecoder('utf-7')
        s = '+3ADYAA-'
        raises(UnicodeError, decode, s, len(s), None)
        def replace_handler(errors, codec, message, input, start, end):
            return u'?', end
        assert decode(s, len(s), None, final=True,
                      errorhandler = replace_handler) == (u'??', len(s))


class TestEncoding(UnicodeTests):
    def test_all_ascii(self):
        for i in range(128):
            if sys.version >= "2.7":
                self.checkencode(unichr(i), "utf-7")
            for encoding in "utf-8 latin-1 ascii".split():
                self.checkencode(unichr(i), encoding)

    def test_all_first_256(self):
        for i in range(256):
            if sys.version >= "2.7":
                self.checkencode(unichr(i), "utf-7")
            for encoding in ("utf-8 utf-16 utf-16-be utf-16-le "
                             "utf-32 utf-32-be utf-32-le").split():
                self.checkencode(unichr(i), encoding)

    def test_first_10000(self):
        for i in range(10000):
            if sys.version >= "2.7":
                self.checkencode(unichr(i), "utf-7")
            for encoding in ("utf-8 utf-16 utf-16-be utf-16-le "
                             "utf-32 utf-32-be utf-32-le").split():
                self.checkencode(unichr(i), encoding)

    def test_random(self):
        for i in range(10000):
            v = random.randrange(sys.maxunicode)
            if 0xd800 <= v <= 0xdfff:
                continue
            uni = unichr(v)
            if sys.version >= "2.7":
                self.checkencode(uni, "utf-7")
            for encoding in ("utf-8 utf-16 utf-16-be utf-16-le "
                             "utf-32 utf-32-be utf-32-le").split():
                self.checkencode(uni, encoding)                

    def test_maxunicode(self):
        uni = unichr(sys.maxunicode)
        if sys.version >= "2.7":
            self.checkencode(uni, "utf-7")
        for encoding in ("utf-8 utf-16 utf-16-be utf-16-le "
                         "utf-32 utf-32-be utf-32-le").split():
            self.checkencode(uni, encoding)        

    def test_single_chars_utf8(self):
        # check every number of bytes per char
        for s in ["\xd7\x90", "\xd6\x96", "\xeb\x96\x95", "\xf0\x90\x91\x93"]:
            self.checkencode(s, "utf-8")

    def test_utf8_surrogates(self):
        # check replacing of two surrogates by single char while encoding
        # make sure that the string itself is not marshalled
        u = u"\ud800" 
        for i in range(4):
            u += u"\udc00"
        self.checkencode(u, "utf-8")

    def test_ascii_error(self):
        self.checkencodeerror(u"abc\xFF\xFF\xFFcde", "ascii", 3, 6)

    def test_latin1_error(self):
        self.checkencodeerror(u"abc\uffff\uffff\uffffcde", "latin-1", 3, 6)

    def test_mbcs(self):
        if sys.platform != 'win32':
            py.test.skip("mbcs encoding is win32-specific")
        self.checkencode(u'encoding test', "mbcs")
        self.checkdecode('decoding test', "mbcs")
        # XXX test this on a non-western Windows installation
        self.checkencode(u"\N{GREEK CAPITAL LETTER PHI}", "mbcs") # a F
        self.checkencode(u"\N{GREEK CAPITAL LETTER PSI}", "mbcs") # a ?

class TestTranslation(object):
    def setup_class(cls):
        if runicode.MAXUNICODE != sys.maxunicode:
            py.test.skip("these tests cannot run on the llinterp")

    def test_utf8(self):
        from pypy.rpython.test.test_llinterp import interpret
        def f(x):
            
            s1 = "".join(["\xd7\x90\xd6\x96\xeb\x96\x95\xf0\x90\x91\x93"] * x)
            u, consumed = runicode.str_decode_utf_8(s1, len(s1), True)
            s2 = runicode.unicode_encode_utf_8(u, len(u), True)
            return s1 == s2
        res = interpret(f, [2])
        assert res

    def test_surrogates(self):
        if runicode.MAXUNICODE < 65536:
            py.test.skip("Narrow unicode build")
        from pypy.rpython.test.test_llinterp import interpret
        def f(x):
            u = runicode.UNICHR(x)
            t = runicode.ORD(u)
            return t
            
        res = interpret(f, [0x10140])
        assert res == 0x10140
