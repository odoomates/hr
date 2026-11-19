import logging

from odoo import SUPERUSER_ID, http
from odoo.http import request

from .. import adms

_logger = logging.getLogger(__name__)

# a device never sends more at once, even a full download of its punches
MAX_BODY = 20 * 1024 * 1024
OPERLOG_TABLES = ('OPERLOG', 'USERINFO', 'FINGERTMP', 'BIODATA')


class BiometricAdms(http.Controller):
    """ The URLs the ZKTeco and eSSL devices call in ADMS (push) mode. They are fixed by the devices: the database
    comes from the domain name (dbfilter) or is the only one. """

    def _device(self, serial_number):
        """ :return: the active ADMS device of `serial_number` calling from an allowed address, or None """
        request.update_env(user=SUPERUSER_ID)
        device = request.env['hr.biometric.device']
        if serial_number:
            device = device.search([('serial_number', '=', serial_number), ('protocol', '=', 'adms')], limit=1)
        address = request.httprequest.remote_addr
        if not device or not device._accepts_ip(address):
            _logger.info('Biometric device %r refused from %s', serial_number, address)
            return None
        return device.with_company(device.company_id)

    @staticmethod
    def _text(body, status=200):
        return request.make_response(body, headers=[('Content-Type', 'text/plain')], status=status)

    def _refused(self):
        return self._text('Unknown device', status=403)

    @staticmethod
    def _body():
        if (request.httprequest.content_length or 0) > MAX_BODY:
            return None
        return request.httprequest.get_data()[:MAX_BODY].decode('utf-8', errors='replace')

    @http.route('/iclock/cdata', type='http', auth='none', methods=['GET', 'POST'], csrf=False,
                save_session=False)
    def cdata(self, **kwargs):
        device = self._device(kwargs.get('SN'))
        if not device:
            return self._refused()
        if request.httprequest.method == 'GET':
            device._touch()
            return self._text(device._adms_handshake())
        body = self._body()
        if body is None:
            return self._text('Too large', status=413)
        table = (kwargs.get('table') or '').upper()
        stamp = kwargs.get('Stamp') or kwargs.get('OpStamp')
        count = 0
        if table == 'ATTLOG':
            count = device._adms_attlog(body, stamp)
        elif table in OPERLOG_TABLES:
            count = device._adms_operlog(body, stamp)
        if table == 'OPTIONS':
            device._touch(adms.parse_info(body))
        else:
            device._touch()
        return self._text('OK:%d' % count)

    @http.route('/iclock/getrequest', type='http', auth='none', methods=['GET'], csrf=False, save_session=False)
    def getrequest(self, **kwargs):
        device = self._device(kwargs.get('SN'))
        if not device:
            return self._refused()
        device._touch(adms.parse_getrequest_info(kwargs.get('INFO')))
        return self._text(device._adms_command_lines() or 'OK')

    @http.route('/iclock/devicecmd', type='http', auth='none', methods=['POST'], csrf=False, save_session=False)
    def devicecmd(self, **kwargs):
        device = self._device(kwargs.get('SN'))
        if not device:
            return self._refused()
        body = self._body()
        if body is None:
            return self._text('Too large', status=413)
        device._touch()
        device._adms_replies(body)
        return self._text('OK')

    @http.route('/iclock/ping', type='http', auth='none', methods=['GET'], csrf=False, save_session=False)
    def ping(self, **kwargs):
        device = self._device(kwargs.get('SN'))
        if not device:
            return self._refused()
        device._touch()
        return self._text('OK')
