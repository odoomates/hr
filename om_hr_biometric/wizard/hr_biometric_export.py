from odoo import fields, models
from odoo.exceptions import UserError


class HrBiometricExport(models.TransientModel):
    """ Enroll employees on devices, or update their name there, with their fingerprints if wanted. """
    _name = 'hr.biometric.export'
    _description = 'Send Employees to Biometric Devices'

    device_ids = fields.Many2many('hr.biometric.device', string='Devices', required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True)
    with_fingerprints = fields.Boolean(
        string='With Their Fingerprints', default=True,
        help='Copy the fingerprints the employees enrolled on another device, so they do not enroll again: read '
             'from a TCP device, or kept in Odoo for ADMS devices.')

    def action_export(self):
        others = self.employee_ids.filtered(lambda e: e.company_id not in self.device_ids.company_id)
        if others:
            raise UserError(self.env._('No device of the company of %s is selected.', ', '.join(others.mapped('name'))))
        copied = 0
        plain = self.employee_ids
        if self.with_fingerprints:
            plain = self.env['hr.employee']
            for employee in self.employee_ids:
                if self._send_with_fingerprints(employee):
                    copied += 1
                else:
                    plain |= employee
        if plain:
            self.device_ids._push_users(plain)
        return self.device_ids._notify(self.env._(
            '%(total)s employees are sent at the next contact of the devices, %(copied)s with their fingerprints.',
            total=len(self.employee_ids), copied=copied))

    def _send_with_fingerprints(self, employee):
        """ Copy `employee` with the fingerprints of one of its device users to the devices that lack them.
            :return: whether fingerprints were found """
        for source in employee.sudo().biometric_user_ids.filtered(lambda u: u.state != 'to_delete'):
            targets = self.device_ids.filtered(lambda d, s=source: d != s.device_id
                                               and d.company_id == employee.company_id)
            if not targets:
                continue
            templates = source.device_id._read_templates(source)
            if templates:
                for target in targets:
                    target._write_templates(source, templates)
                return True
        return False
