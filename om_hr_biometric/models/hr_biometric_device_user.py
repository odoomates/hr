import unicodedata

from odoo import api, fields, models
from odoo.exceptions import UserError

from .. import adms

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

    _user_uniq = models.Constraint('UNIQUE(device_id, user_code)', 'A user ID is used once per device.')

    @api.depends('user_code', 'name')
    def _compute_display_name(self):
        for user in self:
            user.display_name = '%s - %s' % (user.user_code, user.name) if user.name else user.user_code

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
        """ Link the users to an employee of their company: the one with their biometric ID, else the only one with
            their name, the same without accents, or starting with it (a device keeps 24 characters of a name). An
            employee found by name and without a biometric ID gets the user ID of the device. """
        Employee = self.env['hr.employee'].sudo()
        for company, users in self.grouped('company_id').items():
            employees = Employee.search([('company_id', 'in', (company.id, False))])
            by_code = {employee.biometric_code: employee for employee in employees if employee.biometric_code}
            for user in users:
                employee = by_code.get(user.user_code) or self._employee_by_name(user.name, employees)
                if not employee:
                    continue
                user.employee_id = employee
                if not employee.biometric_code and user.user_code not in by_code:
                    employee.biometric_code = user.user_code
                    by_code[user.user_code] = employee

    @staticmethod
    def _employee_by_name(name, employees):
        """ :return: the only employee whose name is `name`, compared exactly, then without accents and case, then as
            the start of the name; nothing when several match """
        def plain(text):
            text = unicodedata.normalize('NFKD', text or '')
            return ' '.join(''.join(c for c in text if not unicodedata.combining(c)).casefold().split())
        name = ' '.join((name or '').split())
        if len(name) < 3:
            return employees.browse()
        for match in (lambda e: ' '.join(e.name.split()) == name,
                      lambda e: plain(e.name) == plain(name),
                      lambda e: plain(e.name).startswith(plain(name))):
            found = employees.filtered(match)
            if len(found) == 1:
                return found
            if len(found) > 1:
                return employees.browse()
        return employees.browse()

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
            raise UserError(self.env._(
                'No fingerprint of %(user)s to copy from %(device)s: over ADMS, the fingerprints are copied once Odoo '
                'keeps them (Attendances > Settings > Biometric Devices) and the device has sent them.',
                user=self.display_name, device=self.device_id.name))
        for device in devices - self.device_id:
            device._write_templates(self, templates)

    def action_open_copy(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Copy to Other Devices'),
            'res_model': 'hr.biometric.copy',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_device_user_id': self.id},
        }

    def action_open_enroll(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Enroll a Fingerprint'),
            'res_model': 'hr.biometric.enroll',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_device_user_id': self.id},
        }

    def action_remove_from_device(self):
        for device, users in self.grouped('device_id').items():
            device._remove_users(users)
