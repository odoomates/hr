""" ADMS (push) protocol of the ZKTeco and eSSL devices: parsing of what the devices send, and the lines Odoo
answers. Plain functions, without Odoo, so that they are easy to test. """
import re
from datetime import datetime
from urllib.parse import parse_qsl

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
# a name on the device holds 24 characters at most
NAME_SIZE = 24


def parse_attlog(body):
    """ :return: the punches of an ATTLOG upload, as dicts (user_code, local_time, status, verify_code, work_code);
        lines that cannot be read are left out. A line is `PIN, time, status, verify, work code, ...`, tab
        separated. """
    punches = []
    for line in (body or '').splitlines():
        fields = line.strip('\r\n').split('\t')
        if len(fields) < 2 or not fields[0].strip():
            continue
        try:
            local_time = datetime.strptime(fields[1].strip(), DATETIME_FORMAT)
        except ValueError:
            continue
        punches.append({
            'user_code': fields[0].strip(),
            'local_time': local_time,
            'status': fields[2].strip() if len(fields) > 2 else '',
            'verify_code': fields[3].strip() if len(fields) > 3 else '',
            'work_code': fields[4].strip() if len(fields) > 4 else '',
        })
    return punches


def parse_key_values(text, separator='\t'):
    """ :return: dict of `key=value` pairs, keys in lower case. """
    values = {}
    for pair in text.split(separator):
        key, equal, value = pair.partition('=')
        if equal and key.strip():
            values[key.strip().lstrip('~').lower()] = value.strip()
    return values


def parse_operlog(body):
    """ :return: (users, biometrics) of an OPERLOG, USERINFO, FINGERTMP or BIODATA upload: the users as dicts of
        their keys (pin, name, pri, card...), and the fingerprint and face templates as dicts (pin, kind 'finger' or
        'face', index, valid, data: the template in base64). Operation log lines are left out. """
    users, biometrics = [], []
    for line in (body or '').splitlines():
        line = line.strip('\r\n')
        tag, _space, rest = line.partition(' ')
        tag = tag.upper()
        if tag in ('USER', 'FP', 'FACE', 'BIODATA'):
            values = parse_key_values(rest)
        elif tag.startswith('PIN='):
            # some firmwares send the users without the USER tag
            tag, values = 'USER', parse_key_values(line)
        else:
            continue
        pin = values.get('pin')
        if not pin:
            continue
        if tag == 'USER':
            users.append(values)
            continue
        if tag == 'BIODATA':
            # Type: 1 fingerprint, 2 face (near infrared), 9 face (visible light); No: the finger
            kind, index = ('finger' if values.get('type', '1') == '1' else 'face'), values.get('no', '0')
        else:
            kind, index = ('finger' if tag == 'FP' else 'face'), values.get('fid', '0')
        biometrics.append({
            'pin': pin,
            'kind': kind,
            'index': int(index) if index.isdigit() else 0,
            'valid': values.get('valid', '1') != '0',
            'data': values.get('tmp') or '',
        })
    return users, biometrics


def parse_info(text):
    """ :return: the device information of a `table=options` upload or of the answer to INFO: `key=value` pairs
        separated by commas or line breaks. """
    values = {}
    for part in re.split(r'[,\r\n]', text or ''):
        values.update(parse_key_values(part))
    return values


def parse_getrequest_info(info):
    """ :return: the device information sent with the INFO argument of /iclock/getrequest: firmware, numbers of
        users, fingerprints and punches, IP address, ... comma separated. """
    keys = ['fwversion', 'usercount', 'fpcount', 'transactioncount', 'ipaddress']
    return {key: value.strip() for key, value in zip(keys, (info or '').split(','), strict=False) if value.strip()}


def parse_command_replies(body):
    """ :return: list of (command id, return code, data) of the replies to commands: a line
        `ID=12&Return=0&CMD=DATA`, followed by the data of the command if any. """
    replies = []
    for line in (body or '').splitlines():
        if line.startswith('ID='):
            values = dict(parse_qsl(line, keep_blank_values=True))
            try:
                replies.append([int(values.get('ID')), int(values.get('Return', '0')), ''])
            except (TypeError, ValueError):
                continue
        elif replies and line.strip():
            replies[-1][2] += line + '\n'
    return [tuple(reply) for reply in replies]


def clean(value, size=None):
    """ :return: `value` without the characters that break a command line. """
    value = re.sub(r'[\t\r\n]+', ' ', value or '').strip()
    return value[:size] if size else value


def user_update_command(pin, name, privilege=0, card=''):
    fields = ['PIN=%s' % clean(pin), 'Name=%s' % clean(name, NAME_SIZE), 'Pri=%s' % privilege]
    if card:
        fields.append('Card=%s' % clean(card))
    return 'DATA UPDATE USERINFO ' + '\t'.join(fields)


def user_delete_command(pin):
    return 'DATA DELETE USERINFO PIN=%s' % clean(pin)


def template_update_command(pin, index, data):
    """ `data`: the fingerprint template in base64 """
    return 'DATA UPDATE FINGERTMP PIN=%s\tFID=%d\tSize=%d\tValid=1\tTMP=%s' % (clean(pin), index, len(data), data)


def enroll_command(pin, index):
    return 'ENROLL_FP PIN=%s\tFID=%d\tRETRY=3\tOVERWRITE=1' % (clean(pin), index)


def query_logs_command(start, end):
    return 'DATA QUERY ATTLOG StartTime=%s\tEndTime=%s' % (start.strftime(DATETIME_FORMAT),
                                                          end.strftime(DATETIME_FORMAT))


def encode_time(local_time):
    """ :return: `local_time` in the number of seconds the ZKTeco devices use for their clock. """
    days = ((local_time.year - 2000) * 12 + local_time.month - 1) * 31 + local_time.day - 1
    return (days * 24 * 60 * 60 + (local_time.hour * 60 + local_time.minute) * 60 + local_time.second)


def set_time_command(local_time):
    return 'SET OPTIONS DateTime=%d' % encode_time(local_time)


def timezone_option(offset):
    """ :return: the TimeZone option of the handshake for an offset to UTC (a timedelta): in hours, or in minutes
        for the zones that are not a whole number of hours away. """
    minutes = int(offset.total_seconds() // 60)
    return str(minutes // 60) if not minutes % 60 else str(minutes)


def handshake(serial_number, attlog_stamp, operlog_stamp, timezone):
    """ :return: the options Odoo answers to the first request of the device. """
    return '\n'.join([
        'GET OPTION FROM: %s' % serial_number,
        'ATTLOGStamp=%s' % (attlog_stamp or 'None'),
        'OPERLOGStamp=%s' % (operlog_stamp or 'None'),
        'ATTPHOTOStamp=None',
        'ErrorDelay=30',
        'Delay=10',
        'TransTimes=00:00;14:05',
        'TransInterval=1',
        'TransFlag=TransData AttLog OpLog EnrollUser ChgUser EnrollFP ChgFP FACE',
        'TimeZone=%s' % timezone,
        'Realtime=1',
        'Encrypt=None',
    ]) + '\n'
