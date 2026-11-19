""" A fake ZKTeco device on a local TCP port, answering like a colour device (72-byte users, 40-byte punches). """
import socket
import struct
import threading

from odoo.addons.om_hr_biometric.adms import encode_time

from .. import zk_client as zk


class FakeDevice:

    def __init__(self, password=0, users=(), punches=(), templates=()):
        self.password = password
        self.users = {user_id: name for user_id, name in users}
        self.templates = {}  # user_id: {finger: template}
        for user_id, index, data in templates:
            self.templates.setdefault(user_id, {})[index] = data
        self.upload = b''
        self.enrolled = []
        self.punches = list(punches)  # (user_id, local datetime, status, verify)
        self.disabled = 0
        self.cleared = False
        self.buffer = b''
        self.server = socket.create_server(('127.0.0.1', 0))
        self.port = self.server.getsockname()[1]
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def close(self):
        self.server.close()

    def _serve(self):
        while True:
            try:
                connection, _address = self.server.accept()
            except OSError:
                return
            with connection:
                self._session(connection)

    def _session(self, connection):
        session_id, authenticated = 4321, not self.password
        while True:
            prefix = self._receive(connection, 8)
            if not prefix:
                return
            packet = self._receive(connection, struct.unpack('<I', prefix[4:])[0])
            command, _checksum, _session, reply_id = struct.unpack('<4H', packet[:8])
            data = packet[8:]
            if command == zk.CMD_AUTH:
                authenticated = data == zk.comm_key(self.password, session_id)
            if command in (zk.CMD_CONNECT, zk.CMD_AUTH) or not authenticated:
                replies = [(zk.CMD_ACK_OK if authenticated else zk.CMD_ACK_UNAUTH, b'')]
            else:
                replies = self._answer(command, data)
            for reply, reply_data in replies:
                self._reply(connection, reply, session_id, reply_id, reply_data)
            if command == zk.CMD_EXIT:
                return

    def _answer(self, command, data):
        """ :return: the (command, data) replies of the device to `command` """
        ok = (zk.CMD_ACK_OK, b'')
        if command == zk.CMD_PREPARE_BUFFER:
            wanted = struct.unpack('<bhii', data)[1]
            self.buffer = {zk.CMD_USERTEMP_RRQ: self._users_buffer,
                           zk.CMD_DB_RRQ: self._templates_buffer}.get(wanted, self._punches_buffer)()
            return [(zk.CMD_ACK_OK, b'\x00' + struct.pack('<I', len(self.buffer)))]
        if command == zk.CMD_READ_BUFFER:
            start, size = struct.unpack('<ii', data)
            return [(zk.CMD_PREPARE_DATA, struct.pack('<I', size)), (zk.CMD_DATA, self.buffer[start:start + size]),
                    ok]
        if command == zk.CMD_GET_FREE_SIZES:
            fields = [0] * 20
            fields[4], fields[8] = len(self.users), len(self.punches)
            return [(zk.CMD_ACK_OK, struct.pack('<20i', *fields))]
        if command == zk.CMD_OPTIONS_RRQ:
            name = data.rstrip(b'\x00').decode()
            value = {'~SerialNumber': 'FAKE123', '~DeviceName': 'FakeFace'}.get(name, '')
            return [(zk.CMD_ACK_OK, ('%s=%s\x00' % (name, value)).encode())]
        if command == zk.CMD_GET_VERSION:
            return [(zk.CMD_ACK_OK, b'Ver 6.60\x00')]
        if command == zk.CMD_USER_WRQ:
            record = zk.USER_72.unpack(data)
            self.users[zk.text(record[6])] = zk.text(record[3])
        elif command == zk.CMD_DELETE_USER:
            uid = struct.unpack('<H', data)[0]
            self.users.pop(list(self.users)[uid - 1], None)
        elif command == zk.CMD_CLEAR_ATTLOG:
            self.punches, self.cleared = [], True
        elif command == zk.CMD_PREPARE_DATA:
            self.upload = b''
        elif command == zk.CMD_DATA:
            self.upload += data
        elif command == zk.CMD_SAVE_USERTEMPS:
            self._save_upload()
        elif command == zk.CMD_STARTENROLL:
            user_id, index, _flag = struct.unpack('<24sbb', data)
            self.enrolled.append((zk.text(user_id), index))
        elif command in (zk.CMD_DISABLEDEVICE, zk.CMD_ENABLEDEVICE):
            self.disabled += 1 if command == zk.CMD_DISABLEDEVICE else -1
        return [ok]

    @staticmethod
    def _receive(connection, size):
        data = b''
        while len(data) < size:
            part = connection.recv(size - len(data))
            if not part:
                return b''
            data += part
        return data

    @staticmethod
    def _reply(connection, command, session_id, reply_id, data=b''):
        packet = zk.make_packet(command, session_id, reply_id, data)
        connection.sendall(zk.TCP_MAGIC + struct.pack('<I', len(packet)) + packet)

    def _users_buffer(self):
        records = b''.join(zk.USER_72.pack(uid, 0, b'', name.encode(), 0, b'1', user_id.encode())
                           for uid, (user_id, name) in enumerate(self.users.items(), start=1))
        return struct.pack('<I', len(records)) + records

    def _templates_buffer(self):
        uids = {user_id: uid for uid, user_id in enumerate(self.users, start=1)}
        records = b''.join(zk.TEMPLATE_HEADER.pack(zk.TEMPLATE_HEADER.size + len(data), uids[user_id], index, 1) + data
                           for user_id, fingers in self.templates.items() for index, data in fingers.items())
        return struct.pack('<I', len(records)) + records

    def _save_upload(self):
        users_size, table_size, _fingers_size = struct.unpack('<III', self.upload[:12])
        users = self.upload[12:12 + users_size]
        table = self.upload[12 + users_size:12 + users_size + table_size]
        fingers = self.upload[12 + users_size + table_size:]
        uids = {}
        for offset in range(0, len(users), zk.USER_WRITE_73.size):
            record = zk.USER_WRITE_73.unpack(users[offset:offset + zk.USER_WRITE_73.size])
            uids[record[1]] = zk.text(record[7])
            self.users[zk.text(record[7])] = zk.text(record[4])
        for offset in range(0, len(table), zk.TEMPLATE_ENTRY.size):
            _two, uid, index, start = zk.TEMPLATE_ENTRY.unpack(table[offset:offset + zk.TEMPLATE_ENTRY.size])
            size = struct.unpack('<H', fingers[start:start + 2])[0]
            self.templates.setdefault(uids[uid], {})[index - 0x10] = fingers[start + 2:start + 2 + size]

    def _punches_buffer(self):
        records = b''.join(zk.PUNCH_40.pack(0, user_id.encode(), verify, struct.pack('<I', encode_time(when)),
                                            status, b'')
                           for user_id, when, status, verify in self.punches)
        return struct.pack('<I', len(records)) + records
