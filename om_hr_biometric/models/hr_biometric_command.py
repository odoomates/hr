from datetime import timedelta

from odoo import api, fields, models

from .. import adms

COMMANDS = [
    ('user_update', 'Send User'),
    ('user_delete', 'Remove User'),
    ('template_update', 'Send Fingerprint'),
    ('enroll_fp', 'Enroll Fingerprint'),
    ('query_logs', 'Download Punches'),
    ('query_users', 'Download Users'),
    ('info', 'Device Information'),
    ('set_time', 'Set Time'),
    ('reboot', 'Restart'),
]
# a command sent without reply is sent again after this delay, up to MAX_TRIES times
RETRY_DELAY = timedelta(minutes=10)
MAX_TRIES = 3
# commands done or failed are deleted after
KEEP_COMMANDS = timedelta(days=180)


class HrBiometricCommand(models.Model):
    """ A command for a device. ADMS devices collect the pending commands when they call, run them and reply. """
    _name = 'hr.biometric.command'
    _description = 'Biometric Device Command'
    _order = 'id desc'
    _rec_name = 'command'

    device_id = fields.Many2one('hr.biometric.device', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='device_id.company_id', store=True, index=True)
    command = fields.Selection(COMMANDS, required=True)
    payload = fields.Char(required=True, help='The command line as the device reads it.')
    device_user_id = fields.Many2one('hr.biometric.device.user', ondelete='set null')
    state = fields.Selection([('pending', 'Pending'), ('sent', 'Sent'), ('done', 'Done'), ('failed', 'Failed')],
                             required=True, default='pending', index=True)
    tries = fields.Integer(readonly=True)
    sent_date = fields.Datetime(readonly=True)
    done_date = fields.Datetime(readonly=True)
    return_code = fields.Integer(readonly=True)
    reply = fields.Text(readonly=True)

    @api.model
    def _to_send(self, device, limit):
        """ :return: the commands of `device` to send now: pending, or sent without reply for a while; those sent
            too many times fail. """
        late = fields.Datetime.now() - RETRY_DELAY
        stale = self.search([('device_id', '=', device.id), ('state', '=', 'sent'), ('sent_date', '<', late)])
        stale.filtered(lambda c: c.tries >= MAX_TRIES).write({
            'state': 'failed', 'reply': self.env._('No reply from the device.')})
        return self.search([('device_id', '=', device.id), '|', ('state', '=', 'pending'),
                            '&', ('state', '=', 'sent'), ('sent_date', '<', late)], order='id', limit=limit)

    def _mark_sent(self):
        now = fields.Datetime.now()
        for command in self:
            command.write({'state': 'sent', 'sent_date': now, 'tries': command.tries + 1})

    def _adms_line(self):
        self.ensure_one()
        return 'C:%d:%s' % (self.id, self.payload)

    def _on_reply(self, code, data):
        """ The device ran the command: `code` is 0 or more when it succeeded. """
        self.ensure_one()
        self.write({'state': 'done' if code >= 0 else 'failed', 'return_code': code, 'reply': data or False,
                    'done_date': fields.Datetime.now()})
        if code < 0:
            return
        user = self.device_user_id
        if self.command == 'user_update' and user.state == 'to_push':
            user.state = 'on_device'
        elif self.command == 'user_delete' and user.state == 'to_delete':
            user.unlink()
        elif self.command == 'info' and data:
            self.device_id._touch(adms.parse_info(data))

    @api.model
    def _cron_cleanup(self):
        """ Delete the commands done or failed long ago. """
        limit = fields.Datetime.now() - KEEP_COMMANDS
        self.sudo().search([('state', 'in', ('done', 'failed')), ('create_date', '<', limit)]).unlink()

    def action_retry(self):
        self.filtered(lambda c: c.state == 'failed').write({'state': 'pending', 'tries': 0})

    def action_cancel(self):
        self.filtered(lambda c: c.state in ('pending', 'sent')).write({
            'state': 'failed', 'reply': self.env._('Cancelled.')})
