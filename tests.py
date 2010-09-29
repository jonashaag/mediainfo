import unittest2 as unittest
import mediainfo
from functools import partial
from mediainfo import lowlevel
from mediainfo.lowlevel import SECTION_SEP, PARAM_SEP, \
                               _format_inform, _prepare_inform, \
                               _parse_inform_output, _lambda_x_x

from os.path import join, dirname, normpath, basename, abspath, realpath
from os import pardir, listdir
def _get_files(*j):
    dir = join(*j)
    return [join(dir, file) for file in listdir(dir)]

_this_dir = abspath(dirname(realpath(__file__)))
TEST_FILES_DIR = abspath(join(_this_dir, pardir, 'test_data'))
IMAGE_TEST_FILES = _get_files(TEST_FILES_DIR, 'images')
VIDEO_TEST_FILES = _get_files(TEST_FILES_DIR, 'videos')
INVALID_TEST_FILES = _get_files(TEST_FILES_DIR, 'invalid')

def slugify(s):
    s = s.lower()
    buf = []
    for char in s:
        if char == '.':
            char = '_'
        if char in 'abcdefghijklmnopqrstuvwxzy012345679_':
            buf.append(char)
    if buf[0] in '0123456789':
        buf.pop(0)
    return ''.join(buf)

class LowlevelTestcase(unittest.TestCase):
    def test_module(self):
        self.assert_(mediainfo.get_metadata)
        self.assert_(mediainfo.ExecutionError)

    def test_pepare_inform(self):
        self.assertRaises(AssertionError, _prepare_inform, {})
        self.assertEqual(
            _prepare_inform({'Foo' : 'A'}),
            {'Foo' : [('A', _lambda_x_x)]}
        )
        self.assertEqual(
            _prepare_inform({'Foo' : ['A', ('B', int)]}),
            {'Foo' : [('A', _lambda_x_x), ('B', int)]}
        )
        self.assertEqual(
            _prepare_inform({'Blah' : {'hello' : float, 'foo' : None},
                             'Fizz' : ['A', ('b', object), 'B']}),
            {'Blah' : {'hello' : float, 'foo' : None}.items(),
             'Fizz' : [('A', _lambda_x_x), ('b', object), ('B', _lambda_x_x)]}
        )

    def test_parse_inform_output(self):
        _safe_int = lambda s: -1 if s == '' else int(s)
        self.assertEqual(_parse_inform_output('', object()), {})
        query = {'A' : [('A', int), 'B', ('C', str)],
                 'B' : [('X', float), ('Y', _safe_int)]}
        query = _prepare_inform(query)
        outp = 'A:-1337' + PARAM_SEP + 'asdf' + PARAM_SEP + 'ghjk' + \
                SECTION_SEP + 'B:3.14' + PARAM_SEP + '' + SECTION_SEP
        self.assertEqual(_parse_inform_output(outp, query),
                         {'A' : {'A' : -1337, 'B' : 'asdf', 'C' : 'ghjk'},
                          'B' : {'X' : 3.14, 'Y' : -1}})
        outp2 = outp.replace('-1337', 'xxx')
        self.assertRaisesRegexp(
            ValueError, "invalid literal for int\(\) with base 10: 'xxx'",
            _parse_inform_output, outp2, query
        )
        outp3 = outp.replace('-1337', '')
        self.assertEqual(_parse_inform_output(outp3, query)['A']['A'], 0)
        def valerr(x):
            raise ValueError("hello-there")
        self.assertRaisesRegexp(
            ValueError, "hello-there",
            _parse_inform_output, 'A:', {'A' : [('x', valerr)]}
        )

    def test_format_inform(self):
        self.assertEqual(_format_inform({}), SECTION_SEP)
        self.assertEqual(_format_inform({'Foo' : []}),
                         'Foo;Foo:' + SECTION_SEP)
        self.assertEqual(
            _format_inform({ 'Hello_World' : [('Blah', None), ('Name', type)]}),
            'Hello_World;Hello_World:%Blah%' + PARAM_SEP + '%Name%' + SECTION_SEP
        )
        self.assertEqual(_format_inform({
            'A' : [('a', None), ('b', None), ('c', None)],
            'B' : [('d', None), ('fg', int)]}),
            'A;A:%a%' + PARAM_SEP + '%b%' + PARAM_SEP + '%c%' + SECTION_SEP +
            '\r\n' + 'B;B:%d%' + PARAM_SEP + '%fg%' + SECTION_SEP
        )

    query = {
        'General' : {
            'VideoCount' : int,
            'ImageCount' : int
        },
        'Video' : {
            'Width' : int,
            'Height' : int,
            'BitRate' : lambda *x:int(float(*x)),
            'FrameRate' : float,
            'Duration' : int,
            'PixelAspectRatio' : float,
            'Format' : str
        },
        'Image' : {
            'Width' : int,
            'Height' : int,
            'Format' : str
        }
    }

    def _test_valid(self, type_, not_type, file):
        meta = mediainfo.get_metadata(file, **self.query)
        self.assert_(meta['General'][type_ + 'Count'])
        self.assert_(meta['General'][not_type + 'Count'] == 0)
        for attr, attrtype in self.query[type_].iteritems():
            self.assertEqual(type(meta[type_][attr]), type(attrtype()))
            self.assert_(meta[type_][attr], 'missing %s:%s key' % (type_, attr))
        self.assert_(not_type not in meta)

    def _test_invalid(self, file):
        meta = mediainfo.get_metadata(file, **self.query)
        self.assert_(meta['General']['VideoCount'] == 0)
        self.assert_(meta['General']['ImageCount'] == 0)
        for section in ['Video', 'Image']:
            self.assert_(section not in meta)

    # the following, ugly and hackish code generates test methods
    # for each file, the file name as method name (sanitized).
    # Just look away.
    for type_, not_type, files in [('Video', 'Image', VIDEO_TEST_FILES),
                                   ('Image', 'Video', IMAGE_TEST_FILES)]:
        for file in files:
            tpl = (type_, not_type, file)
            file = slugify(basename(file))
            exec('def test_%s(self):' \
                 '    self._test_valid(*%r)' % (file, tpl))

    for file in INVALID_TEST_FILES:
        exec('def test_%s(self):' \
             '    self._test_invalid(%r)' \
             % (slugify(basename(file)), file))


if __name__ == '__main__':
    unittest.main()
