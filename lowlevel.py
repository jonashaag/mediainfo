import os
import sys
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

_lambda_x_x = lambda x:x

def _raise(*exc_info):
    raise exc_info[0], exc_info[1], exc_info[2]

def _prepare_inform(inform):
    assert inform
    sections = {}
    for section, dirty_params in inform.iteritems():
        if isinstance(dirty_params, dict):
            sections[section] = dirty_params.items()
        elif isinstance(dirty_params, basestring):
            sections[section] = [(dirty_params, _lambda_x_x)]
        else:
            sections[section] = params = []
            for param in dirty_params:
                if isinstance(param, basestring):
                    params.append((param, _lambda_x_x))
                else:
                    params.append(param)
    return sections

def _format_inform(inform):
    return (SECTION_SEP + '\r\n').join(
        '{section};{section}:'.format(section=section_name) +
        PARAM_SEP.join(r'%{param}%'.format(param=param) for param, _ in params)
        for section_name, params in inform.iteritems()
    ) + SECTION_SEP

def _parse_inform_output(output, inform):
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
        for (param_name, param_type), value in zip(inform[section], values):
            try:
                value = param_type(value)
            except ValueError:
                value_error = sys.exc_info()
                if value == '':
                    # if `value` is an empty string, try `param_type` without
                    # arguments. useful e.g. for `param_type` == `int`,
                    # which does not allow empty strings as argument.
                    try:
                        value = param_type()
                    except (ValueError, TypeError):
                        _raise(*value_error)
                else:
                    _raise(*value_error)
            sec[param_name] = value
        sections[section] = sec
    return sections

def get_metadata(filename, **inform):
    inform = _prepare_inform(inform)
    cmd = ['mediainfo', '--Inform=file://%s' % STDIN_DEVICE, filename]
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, stdin=PIPE)
    stdout, stderr = proc.communicate(input=_format_inform(inform))
    stdout, stderr = map(str.strip, [stdout, stderr])

    if proc.returncode != 0 or stderr:
        raise ExecutionError(cmd, proc.returncode, stderr)

    return _parse_inform_output(stdout, inform)
