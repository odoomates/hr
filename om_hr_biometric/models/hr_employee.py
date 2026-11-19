from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    biometric_code = fields.Char(
        string='Biometric ID', copy=False, index='btree_not_null',
        groups='hr.group_hr_user,hr_attendance.group_hr_attendance_user',
        help='The user ID (PIN) of the employee on the biometric devices.')
    biometric_user_ids = fields.One2many('hr.biometric.device.user', 'employee_id', string='Biometric Devices',
                                         groups='hr.group_hr_user,hr_attendance.group_hr_attendance_user')

    @api.constrains('biometric_code', 'company_id')
    def _check_biometric_code(self):
        for employee in self.filtered('biometric_code'):
            if self.sudo().search_count([('biometric_code', '=', employee.biometric_code),
                                         ('company_id', '=', employee.company_id.id),
                                         ('id', '!=', employee.id)], limit=1):
                raise ValidationError(self.env._('The biometric ID %(code)s is already given to another employee '
                                                 'of %(company)s.', code=employee.biometric_code,
                                                 company=employee.company_id.name))

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        employees.filtered('biometric_code')._link_biometric_users()
        return employees

    def write(self, vals):
        result = super().write(vals)
        if vals.get('biometric_code'):
            self._link_biometric_users()
        return result

    def _link_biometric_users(self):
        """ Link the device users with the biometric ID of the employees, and process their waiting punches. """
        for employee in self:
            users = self.env['hr.biometric.device.user'].sudo().search([
                ('user_code', '=', employee.biometric_code), ('employee_id', '=', False),
                ('company_id', '=', employee.company_id.id),
            ])
            users.write({'employee_id': employee.id})
            self.env['hr.biometric.log'].sudo().search([
                ('user_code', '=', employee.biometric_code), ('state', '=', 'unmapped'),
                ('company_id', '=', employee.company_id.id),
            ])._process()

    def _assign_biometric_code(self):
        """ Give the next free number as biometric ID to the employees without one. """
        for company, employees in self.filtered(lambda e: not e.biometric_code).grouped('company_id').items():
            codes = self.sudo().search([('company_id', '=', company.id),
                                        ('biometric_code', '!=', False)]).mapped('biometric_code')
            number = max([int(code) for code in codes if code.isdigit()], default=0)
            for employee in employees:
                number += 1
                employee.sudo().biometric_code = str(number)

    def action_biometric_send(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Send to Biometric Devices'),
            'res_model': 'hr.biometric.export',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_employee_ids': self.ids},
        }

    def action_biometric_remove(self):
        self.ensure_one()
        users = self.biometric_user_ids.filtered(lambda u: u.state != 'to_delete')
        users.action_remove_from_device()
