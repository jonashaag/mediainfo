import unittest
import mediainfo
from functools import partial
from mediainfo import lowlevel
from mediainfo.lowlevel import SECTION_SEP, PARAM_SEP

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
        if char in 'abcdefghijklmnopqrstuvxyz012345679_':
            buf.append(char)
    if buf[0] in '0123456789':
        buf.pop(0)
    return ''.join(buf)

class LowlevelTestcase(unittest.TestCase):
    def test_module(self):
        self.assert_(mediainfo.get_metadata)
        self.assert_(mediainfo.ExecutionError)

    def test_format_inform(self):
        self.assertEqual(lowlevel.format_inform(), SECTION_SEP)
        self.assertEqual(lowlevel.format_inform(Foo=[]),
                         'Foo;Foo:' + SECTION_SEP)
        self.assertEqual(lowlevel.format_inform(
            Hello_World=['Blah', 'Blubb', ('Name', type)]),
            'Hello_World;Hello_World:%Blah%' + PARAM_SEP + '%Blubb%'
            + PARAM_SEP + '%Name%'
            + SECTION_SEP
        )
        self.assertEqual(lowlevel.format_inform(
            A=('a', 'b', 'c'), B=['d', ('fg', int), 'h']),
            'A;A:%a%' + PARAM_SEP + '%b%' + PARAM_SEP + '%c%' + SECTION_SEP +
            '\r\n' + 'B;B:%d%' + PARAM_SEP + '%fg%' + PARAM_SEP + '%h%'
            + SECTION_SEP
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
            self.assert_(meta[type_][attr])
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
