from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .. import adms
from .common import group_records

# privilege codes of the devices: 0 user, 2 enroller, 6 administrator, 14 super administrator
ADMIN_PRIVILEGE = 14


class HrBiometricDeviceUser(models.Model):
    """ A user enrolled on a device, and the employee it stands for. One employee may be on several devices. """
    _name = 'hr.biometric.device.user'
    _description = 'Biometric Device User'
    _order = 'device_id, user_code'
    _rec_name = 'user_code'

    device_id = fields.Many2one('hr.biometric.device', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='device_id.company_id', store=True, index=True)
    user_code = fields.Char(string='User ID', required=True, index=True,
                            help='The user ID (PIN) on the device; the punches carry it.')
    name = fields.Char(string='Name on Device')
    card = fields.Char(string='Card Number')
    privilege = fields.Selection([('user', 'User'), ('admin', 'Administrator')], required=True, default='user')
    fingerprint_count = fields.Integer(string='Fingerprints', readonly=True)
    face_count = fields.Integer(string='Faces', readonly=True)
    employee_id = fields.Many2one('hr.employee', index=True, domain="[('company_id', 'in', (company_id, False))]")
    template_ids = fields.One2many('hr.biometric.template', 'device_user_id', string='Templates',
                                   groups='hr_attendance.group_hr_attendance_manager')
    state = fields.Selection([('to_push', 'To Send'), ('on_device', 'On Device'), ('to_delete', 'To Remove')],
                             required=True, default='on_device', readonly=True)

    _sql_constraints = [
        ('user_uniq', 'UNIQUE(device_id, user_code)', 'A user ID is used once per device.'),
    ]

    def name_get(self):
        return [(user.id, '%s - %s' % (user.user_code, user.name) if user.name else user.user_code) for user in self]

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users.filtered(lambda u: not u.employee_id)._link_employees()
        users.filtered('employee_id')._process_unmapped()
        return users

    def write(self, vals):
        result = super().write(vals)
        if vals.get('employee_id'):
            self._process_unmapped()
        return result

    def _link_employees(self):
        """ Link the users to the employee of their company with the same biometric ID. """
        for user in self:
            employee = self.env['hr.employee'].sudo().search([
                ('biometric_code', '=', user.user_code), ('company_id', 'in', (user.company_id.id, False)),
            ], limit=1)
            if employee:
                user.employee_id = employee

    def _process_unmapped(self):
        """ Process the punches that waited for these users to have an employee. """
        for user in self:
            self.env['hr.biometric.log'].sudo().search([
                ('device_id', '=', user.device_id.id), ('user_code', '=', user.user_code),
                ('state', '=', 'unmapped'),
            ])._process()

    def _update_command(self):
        self.ensure_one()
        return adms.user_update_command(self.user_code, self.name or self.employee_id.name,
                                        ADMIN_PRIVILEGE if self.privilege == 'admin' else 0, self.card)

    @api.model
    def _sync_from_device(self, device, users, biometrics):
        """ Create or update the users of `device` from what it sent: `users` dicts of their keys, `biometrics` the
            templates (see adms.parse_operlog). """
        existing = {user.user_code: user for user in self.search([('device_id', '=', device.id)])}
        for values in users:
            vals = {
                'name': values.get('name') or False,
                'card': values.get('card') or False,
                'privilege': 'user' if values.get('pri', '0') in ('0', '') else 'admin',
            }
            user = existing.get(values['pin'])
            if user:
                vals = {key: value for key, value in vals.items() if user[key] != value}
                if user.state == 'to_push':
                    vals['state'] = 'on_device'
                if vals:
                    user.write(vals)
            else:
                existing[values['pin']] = self.create(dict(vals, device_id=device.id, user_code=values['pin']))
        self._sync_biometrics(device, existing, biometrics)

    @api.model
    def _sync_biometrics(self, device, existing, biometrics):
        """ Count the templates of the users of `device`, and store them if the company keeps them. """
        templates = {}
        for biometric in biometrics:
            templates.setdefault(biometric['pin'], {})[biometric['kind'], biometric['index']] = biometric
        store = device.company_id.biometric_store_templates
        Template = self.env['hr.biometric.template'].sudo()
        for pin, by_key in templates.items():
            user = existing.get(pin) or self.create({'device_id': device.id, 'user_code': pin})
            existing[pin] = user
            fingers = sum(1 for kind, _index in by_key if kind == 'finger')
            faces = sum(1 for kind, _index in by_key if kind == 'face')
            user.write({'fingerprint_count': max(user.fingerprint_count, fingers),
                        'face_count': max(user.face_count, faces)})
            if store:
                Template._store(user, by_key.values())

    def _templates(self):
        """ :return: the fingerprint templates of the user stored in Odoo, as dicts (index, data in base64) """
        self.ensure_one()
        return [{'index': template.index, 'data': template.data} for template in self.sudo().template_ids
                if template.kind == 'finger' and template.valid and template.data]

    def action_push(self):
        for user in self:
            user.state = 'to_push'
            user.device_id._send_command('user_update', user._update_command(), user)

    def _copy_to(self, devices):
        """ Enroll the user on `devices` with its fingerprints, read from its device. """
        self.ensure_one()
        templates = self.device_id._read_templates(self)
        if not templates:
            raise UserError(_(
                'No fingerprint of %(user)s to copy from %(device)s: over ADMS, the fingerprints are copied once Odoo '
                'keeps them (Attendances > Configuration, Biometric Devices) and the device has sent them.',
                user=self.display_name, device=self.device_id.name))
        for device in devices - self.device_id:
            device._write_templates(self, templates)

    def action_open_copy(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Copy to Other Devices'),
            'res_model': 'hr.biometric.copy',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_device_user_id': self.id},
        }

    def action_open_enroll(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Enroll a Fingerprint'),
            'res_model': 'hr.biometric.enroll',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_device_user_id': self.id},
        }

    def action_remove_from_device(self):
        for device, users in group_records(self, 'device_id').items():
            device._remove_users(users)
