import os
from future_builtins import zip
from subprocess import Popen, PIPE
try:
    # if we're on Django, respect the project settings.
    from django.conf import settings
    STDIN_DEVICE = settings.STDIN_DEVICE
except (ImportError, AttributeError):
    # otherwise, try the environ and fall back to /dev/stdin (Linux)
    STDIN_DEVICE = os.environ.get('STDIN_DEVICE', '/dev/stdin')

SECTION_SEP = chr(1)
PARAM_SEP = chr(2)

class ExecutionError(Exception):
    """ Raised if a MediaInfo command returns an exit code other than 0. """

def format_inform(**inform):
    sections = []
    for section_name, params in inform.iteritems():
        section = []
        section.extend((param if isinstance(param, basestring) else param[0])
                       for param in params)
        sections.append((section_name, section))

    return (SECTION_SEP + '\r\n').join(
        '{section};{section}:'.format(section=section_name) +
        PARAM_SEP.join(r'%{param}%'.format(param=param) for param in params)
        for section_name, params in sections
    ) + SECTION_SEP

def parse_inform_output(output, inform):
    sections = {}
    may_loop = True
    for section in output.split(SECTION_SEP):
        assert may_loop
        if not section:
            may_loop = False
            break
        section, params = section.split(':', 1)
        values = params.split(PARAM_SEP)
        sec = {}
        for inform_param, value in zip(inform[section], values):
            if isinstance(inform_param, basestring):
                name, typefunc = inform_param, lambda x:x
            else:
                name, typefunc = inform_param
            sec[name] = typefunc(value)
        sections[section] = sec
    return sections

def get_metadata(filename, **inform):
    assert inform
    for section, params in inform.iteritems():
        if isinstance(params, basestring):
            inform[section] = [params]
        elif isinstance(params, dict):
            inform[section] = params.items()

    print repr(format_inform(**inform))

    cmd = ['mediainfo', '--Inform=file://%s' % STDIN_DEVICE, filename]
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, stdin=PIPE)
    stdout, stderr = proc.communicate(input=format_inform(**inform))
    stdout, stderr = map(str.strip, [stdout, stderr])
    print repr(stdout)
    print repr(parse_inform_output(stdout, inform))

    if proc.returncode != 0 or stderr:
        raise ExecutionError(cmd, proc.returncode, stderr)

    return parse_inform_output(stdout, inform)
