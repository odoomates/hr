""" Client of the TCP/UDP protocol of the ZKTeco and eSSL devices (port 4370), on the Python standard library only.
Plain Python, without Odoo, so that it is easy to test against a fake device. """
import socket
import struct
from collections import namedtuple
from contextlib import contextmanager, suppress
from datetime import datetime

from odoo.addons.om_hr_biometric.adms import encode_time

CMD_DB_RRQ = 7
CMD_USER_WRQ = 8
CMD_USERTEMP_RRQ = 9
CMD_OPTIONS_RRQ = 11
CMD_ATTLOG_RRQ = 13
CMD_CLEAR_ATTLOG = 15
CMD_DELETE_USER = 18
CMD_GET_FREE_SIZES = 50
CMD_STARTENROLL = 61
CMD_CANCELCAPTURE = 62
CMD_SAVE_USERTEMPS = 110
CMD_GET_TIME = 201
CMD_SET_TIME = 202
CMD_CONNECT = 1000
CMD_EXIT = 1001
CMD_ENABLEDEVICE = 1002
CMD_DISABLEDEVICE = 1003
CMD_RESTART = 1004
CMD_REFRESHDATA = 1013
CMD_GET_VERSION = 1100
CMD_AUTH = 1102
CMD_PREPARE_DATA = 1500
CMD_DATA = 1501
CMD_FREE_DATA = 1502
CMD_PREPARE_BUFFER = 1503
CMD_READ_BUFFER = 1504
CMD_ACK_OK = 2000
CMD_ACK_ERROR = 2001
CMD_ACK_DATA = 2002
CMD_ACK_UNAUTH = 2005
FCT_FINGERTMP = 2
FCT_USER = 5

USHRT_MAX = 65535
TCP_MAGIC = b'\x50\x50\x82\x7d'
# largest piece of a buffer read at once
TCP_CHUNK = 0xFFC0
UDP_CHUNK = 16 * 1024
# pieces of the data written to the device
WRITE_CHUNK = 1024
# user records: 28 bytes on the older black and white devices, 72 bytes on the colour ones
USER_28 = struct.Struct('<HB5s8sIxBhI')
USER_72 = struct.Struct('<HB8s24sIx7sx24s')
# users in a bulk write of users and templates: the read formats with a leading 2
USER_WRITE_29 = struct.Struct('<BHB5s8sIxBhI')
USER_WRITE_73 = struct.Struct('<BHB8s24sIx7sx24s')
# template records: size (with this header), user uid, finger, valid, then the template
TEMPLATE_HEADER = struct.Struct('<HHbb')
# entry of a template in a bulk write: 2, uid, 0x10 + finger, offset of the template
TEMPLATE_ENTRY = struct.Struct('<bHbI')
# punch records: 8, 16 or 40 bytes depending on the firmware
PUNCH_8 = struct.Struct('<HB4sB')
PUNCH_16 = struct.Struct('<I4sBB2sI')
PUNCH_40 = struct.Struct('<H24sB4sB8s')
OK_REPLIES = (CMD_ACK_OK, CMD_ACK_DATA, CMD_PREPARE_DATA, CMD_DATA)

User = namedtuple('User', 'uid user_id name privilege password card group')
Punch = namedtuple('Punch', 'user_id timestamp status verify work_code')
Template = namedtuple('Template', 'user_id index valid data')


class ZKError(Exception):
    pass


def checksum(packet):
    """ :return: the checksum of `packet` (header with a zero checksum, then data): the sum of its 16-bit words, folded,
        complemented. """
    if len(packet) % 2:
        packet += b'\x00'
    total = 0
    for (word,) in struct.iter_unpack('<H', packet):
        total += word
        if total > USHRT_MAX:
            total -= USHRT_MAX
    return ~total & USHRT_MAX


def make_packet(command, session_id, reply_id, data=b''):
    header = struct.pack('<4H', command, 0, session_id, reply_id)
    return struct.pack('<4H', command, checksum(header + data), session_id, reply_id) + data


def comm_key(key, session_id, ticket=50):
    """ :return: the data of CMD_AUTH for the communication key `key` (a number) of the device. """
    reversed_key = int(f'{key & 0xFFFFFFFF:032b}'[::-1], 2)
    value = struct.pack('<I', (reversed_key + session_id) & 0xFFFFFFFF)
    value = bytes(byte ^ mask for byte, mask in zip(value, b'ZKSO', strict=True))
    value = value[2:] + value[:2]
    ticket &= 0xFF
    return bytes([value[0] ^ ticket, value[1] ^ ticket, ticket, value[3] ^ ticket])


def decode_time(value):
    """ :return: the datetime of the number of seconds the devices use for their clock (see adms.encode_time). """
    second, value = value % 60, value // 60
    minute, value = value % 60, value // 60
    hour, value = value % 24, value // 24
    day, value = value % 31 + 1, value // 31
    month, value = value % 12 + 1, value // 12
    return datetime(value + 2000, month, day, hour, minute, second)


def text(raw):
    return raw.split(b'\x00', 1)[0].decode('utf-8', errors='replace').strip()


class ZKClient:
    """ One connection to a device. Use as a context manager:

        with ZKClient('192.168.1.201') as client:
            punches = client.get_attendance()
    """

    def __init__(self, host, port=4370, timeout=10, password=0, udp=False):
        self.host, self.port, self.timeout, self.password, self.udp = host, port, timeout, int(password or 0), udp
        self.socket = None
        self.session_id = 0
        self.reply_id = USHRT_MAX - 1
        self.user_size = None
        self._users = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc_info):
        self.disconnect()

    # Transport

    def connect(self):
        try:
            if self.udp:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.socket.settimeout(self.timeout)
            else:
                self.socket = socket.create_connection((self.host, self.port), timeout=self.timeout)
        except OSError as error:
            raise ZKError('Cannot reach the device at %s:%s: %s' % (self.host, self.port, error)) from error
        self.session_id = 0
        command, data = self._command(CMD_CONNECT, check=False)
        if command == CMD_ACK_UNAUTH:
            command, data = self._command(CMD_AUTH, comm_key(self.password, self.session_id), check=False)
            if command == CMD_ACK_UNAUTH:
                self._close()
                raise ZKError('The communication key of the device is not the right one.')
        if command not in OK_REPLIES:
            self._close()
            raise ZKError('The device refused the connection (reply %s).' % command)

    def disconnect(self):
        if self.socket:
            with suppress(OSError):
                self._send(CMD_EXIT)
            self._close()

    def _close(self):
        try:
            self.socket.close()
        finally:
            self.socket = None

    def _send(self, command, data=b''):
        self.reply_id = (self.reply_id + 1) % USHRT_MAX
        packet = make_packet(command, self.session_id, self.reply_id, data)
        if self.udp:
            self.socket.sendto(packet, (self.host, self.port))
        else:
            self.socket.sendall(TCP_MAGIC + struct.pack('<I', len(packet)) + packet)

    def _receive_exact(self, size):
        data = b''
        while len(data) < size:
            part = self.socket.recv(size - len(data))
            if not part:
                raise ZKError('The device closed the connection.')
            data += part
        return data

    def _receive(self):
        """ :return: (command, data) of the next packet of the device """
        try:
            if self.udp:
                packet = self.socket.recv(UDP_CHUNK + 1024)
            else:
                prefix = self._receive_exact(8)
                if prefix[:4] != TCP_MAGIC:
                    raise ZKError('The device answered something else than its protocol.')
                packet = self._receive_exact(struct.unpack('<I', prefix[4:])[0])
        except TimeoutError as error:
            raise ZKError('The device did not answer in time.') from error
        except OSError as error:
            raise ZKError('Connection to the device lost: %s' % error) from error
        if len(packet) < 8:
            raise ZKError('The device sent a truncated packet.')
        command, _checksum, session_id, _reply_id = struct.unpack('<4H', packet[:8])
        if command in (CMD_ACK_OK, CMD_ACK_UNAUTH) and not self.session_id:
            self.session_id = session_id
        return command, packet[8:]

    def _command(self, command, data=b'', check=True):
        """ Send a command. :return: (reply command, reply data) """
        if not self.socket:
            raise ZKError('Not connected to the device.')
        try:
            self._send(command, data)
        except OSError as error:
            raise ZKError('Connection to the device lost: %s' % error) from error
        reply, reply_data = self._receive()
        if check and reply not in OK_REPLIES:
            raise ZKError('The device refused command %s (reply %s).' % (command, reply))
        return reply, reply_data

    def _read_buffer(self, command, fct=0, ext=0):
        """ :return: the data the device sends for `command`, read in chunks if large """
        reply, data = self._command(CMD_PREPARE_BUFFER, struct.pack('<bhii', 1, command, fct, ext))
        if reply == CMD_DATA:
            return data
        size = struct.unpack('<I', data[1:5])[0]
        chunk = UDP_CHUNK if self.udp else TCP_CHUNK
        buffer = b''.join(self._read_chunk(start, min(chunk, size - start)) for start in range(0, size, chunk))
        self._command(CMD_FREE_DATA, check=False)
        return buffer

    def _read_chunk(self, start, size):
        reply, data = self._command(CMD_READ_BUFFER, struct.pack('<ii', start, size))
        if reply == CMD_DATA:
            return data
        chunk = b''
        while True:
            reply, data = self._receive()
            if reply == CMD_DATA:
                chunk += data
            elif reply == CMD_ACK_OK:
                return chunk
            else:
                raise ZKError('Unexpected reply %s while reading the device.' % reply)

    def _write_buffer(self, data):
        """ Send `data` to the device, for the command that follows. """
        self._command(CMD_FREE_DATA, check=False)
        self._command(CMD_PREPARE_DATA, struct.pack('<I', len(data)))
        for start in range(0, len(data), WRITE_CHUNK):
            self._command(CMD_DATA, data[start:start + WRITE_CHUNK])

    # Device

    def get_option(self, name):
        _reply, data = self._command(CMD_OPTIONS_RRQ, name.encode() + b'\x00', check=False)
        value = text(data)
        return value.partition('=')[2] if '=' in value else ''

    def get_sizes(self):
        """ :return: dict of the numbers of users, fingerprints, punches and faces on the device """
        _reply, data = self._command(CMD_GET_FREE_SIZES)
        sizes = {'users': 0, 'fingers': 0, 'records': 0, 'faces': 0}
        if len(data) >= 80:
            fields = struct.unpack('<20i', data[:80])
            sizes.update(users=fields[4], fingers=fields[6], records=fields[8])
        if len(data) >= 92:
            sizes['faces'] = struct.unpack('<3i', data[80:92])[0]
        return sizes

    def get_info(self):
        """ :return: the device information, keyed as adms.parse_info """
        _reply, version = self._command(CMD_GET_VERSION)
        sizes = self.get_sizes()
        return {
            'serialnumber': self.get_option('~SerialNumber'),
            'devicename': self.get_option('~DeviceName'),
            'platform': self.get_option('~Platform'),
            'mac': self.get_option('MAC'),
            'fwversion': text(version),
            'usercount': str(sizes['users']),
            'fpcount': str(sizes['fingers']),
            'facecount': str(sizes['faces']),
            'transactioncount': str(sizes['records']),
        }

    def get_time(self):
        _reply, data = self._command(CMD_GET_TIME)
        return decode_time(struct.unpack('<I', data[:4])[0])

    def set_time(self, local_time):
        self._command(CMD_SET_TIME, struct.pack('<I', encode_time(local_time)))

    def restart(self):
        self._command(CMD_RESTART, check=False)

    def clear_attendance(self):
        self._command(CMD_CLEAR_ATTLOG)

    @contextmanager
    def disabled(self):
        """ Lock the keyboard of the device while writing to it: always unlocked again. """
        self._command(CMD_DISABLEDEVICE)
        try:
            yield
        finally:
            self._command(CMD_ENABLEDEVICE, check=False)

    # Users

    def get_users(self):
        """ :return: list of User """
        if self._users is not None:
            return list(self._users)
        records = self.get_sizes()['users']
        data = self._read_buffer(CMD_USERTEMP_RRQ, FCT_USER)
        users = []
        if len(data) > 4:
            total = struct.unpack('<I', data[:4])[0]
            data = data[4:4 + total]
            size = total // records if records else (USER_72.size if not total % USER_72.size else USER_28.size)
            self.user_size = size
            for offset in range(0, total - size + 1, size):
                record = data[offset:offset + size]
                if size == USER_72.size:
                    uid, privilege, password, name, card, group, user_id = USER_72.unpack(record)
                    users.append(User(uid, text(user_id), text(name), privilege, text(password), card, text(group)))
                elif size == USER_28.size:
                    uid, privilege, password, name, card, group, _tz, user_id = USER_28.unpack(record)
                    users.append(User(uid, str(user_id), text(name), privilege, text(password), card, str(group)))
                else:
                    raise ZKError('Unknown user record of %s bytes.' % size)
        self._users = users
        return list(users)

    def set_user(self, user_id, name, privilege=0, card=0):
        """ Create the user `user_id` on the device, or update it. """
        users = self.get_users()
        user = next((u for u in users if u.user_id == str(user_id)), None)
        uid = user.uid if user else max([u.uid for u in users], default=0) + 1
        password = user.password if user else ''
        group = user.group if user and user.group else '1'
        card = int(card or (user.card if user else 0) or 0)
        if self.user_size == USER_28.size:
            if not str(user_id).isdigit():
                raise ZKError('This device takes numeric user IDs only, not %s.' % user_id)
            record = USER_28.pack(uid, privilege, password.encode()[:5], name.encode()[:8], card,
                                  int(group) if group.isdigit() else 1, 0, int(user_id))
        else:
            record = USER_72.pack(uid, privilege, password.encode()[:8], name.encode()[:24], card,
                                  group.encode()[:7], str(user_id).encode()[:24])
        with self.disabled():
            self._command(CMD_USER_WRQ, record)
            self._command(CMD_REFRESHDATA, check=False)
        self._users = [u for u in users if u.uid != uid] + [User(uid, str(user_id), name, privilege, password, card,
                                                                 group)]

    def delete_user(self, user_id):
        """ Remove the user `user_id` from the device. :return: whether it was there """
        users = self.get_users()
        user = next((u for u in users if u.user_id == str(user_id)), None)
        if not user:
            return False
        with self.disabled():
            self._command(CMD_DELETE_USER, struct.pack('<H', user.uid))
            self._command(CMD_REFRESHDATA, check=False)
        self._users = [u for u in users if u.uid != user.uid]
        return True

    # Fingerprints

    def get_templates(self):
        """ :return: list of Template, the fingerprint templates of all the users (data in bytes) """
        data = self._read_buffer(CMD_DB_RRQ, FCT_FINGERTMP)
        if len(data) <= 4:
            return []
        total = struct.unpack('<I', data[:4])[0]
        data = data[4:4 + total]
        users = {user.uid: user.user_id for user in self.get_users()}
        templates, offset = [], 0
        while offset + TEMPLATE_HEADER.size <= len(data):
            size, uid, index, valid = TEMPLATE_HEADER.unpack_from(data, offset)
            if size <= TEMPLATE_HEADER.size:
                break
            templates.append(Template(users.get(uid, str(uid)), index, bool(valid),
                                      data[offset + TEMPLATE_HEADER.size:offset + size]))
            offset += size
        return templates

    def save_user_templates(self, user_id, name, templates, privilege=0, card=0):
        """ Create or update the user `user_id` with its fingerprint `templates` (list of (finger, data in
            bytes)), in one write. """
        users = self.get_users()
        user = next((u for u in users if u.user_id == str(user_id)), None)
        uid = user.uid if user else max([u.uid for u in users], default=0) + 1
        password = (user.password if user else '').encode()
        group = user.group if user and user.group else '1'
        card = int(card or (user.card if user else 0) or 0)
        if self.user_size == USER_28.size:
            if not str(user_id).isdigit():
                raise ZKError('This device takes numeric user IDs only, not %s.' % user_id)
            record = USER_WRITE_29.pack(2, uid, privilege, password[:5], name.encode()[:8], card,
                                        int(group) if group.isdigit() else 1, 0, int(user_id))
        else:
            record = USER_WRITE_73.pack(2, uid, privilege, password[:8], name.encode()[:24], card,
                                        group.encode()[:7], str(user_id).encode()[:24])
        table, fingers = b'', b''
        for index, data in templates:
            table += TEMPLATE_ENTRY.pack(2, uid, 0x10 + index, len(fingers))
            fingers += struct.pack('<H', len(data)) + data
        with self.disabled():
            self._write_buffer(struct.pack('<III', len(record), len(table), len(fingers)) + record + table + fingers)
            self._command(CMD_SAVE_USERTEMPS, struct.pack('<IHH', 12, 0, 8))
            self._command(CMD_REFRESHDATA, check=False)
        self._users = [u for u in users if u.uid != uid] + [User(uid, str(user_id), name, privilege,
                                                                 password.decode(), card, group)]

    def start_enroll(self, user_id, index):
        """ The device asks the user `user_id` for finger `index` (0 to 9), three times. """
        self.get_users()
        if self.user_size == USER_28.size:
            data = struct.pack('<Ibb', int(user_id), index, 1)
        else:
            data = struct.pack('<24sbb', str(user_id).encode(), index, 1)
        self._command(CMD_CANCELCAPTURE, check=False)
        self._command(CMD_STARTENROLL, data)

    # Punches

    def get_attendance(self):
        """ :return: list of Punch, status being the check in / out state, verify the kind of verification """
        records = self.get_sizes()['records']
        data = self._read_buffer(CMD_ATTLOG_RRQ)
        if len(data) <= 4:
            return []
        total = struct.unpack('<I', data[:4])[0]
        data = data[4:4 + total]
        if records:
            size = total // records
        else:
            size = next((s.size for s in (PUNCH_40, PUNCH_16, PUNCH_8) if not total % s.size), PUNCH_8.size)
        users = None
        punches = []
        for offset in range(0, total - size + 1, size):
            record = data[offset:offset + size]
            if size == PUNCH_40.size:
                _uid, user_id, verify, stamp, status, _space = PUNCH_40.unpack(record)
                user_id, work_code = text(user_id), ''
            elif size == PUNCH_16.size:
                user_id, stamp, verify, status, _reserved, work_code = PUNCH_16.unpack(record)
                user_id, work_code = str(user_id), str(work_code)
            elif size == PUNCH_8.size:
                if users is None:
                    users = {user.uid: user.user_id for user in self.get_users()}
                uid, verify, stamp, status = PUNCH_8.unpack(record)
                user_id, work_code = users.get(uid, str(uid)), ''
            else:
                raise ZKError('Unknown punch record of %s bytes.' % size)
            punches.append(Punch(user_id, decode_time(struct.unpack('<I', stamp)[0]), status, verify, work_code))
        return punches
