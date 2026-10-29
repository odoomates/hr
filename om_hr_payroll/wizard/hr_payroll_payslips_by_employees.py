# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipEmployees(models.TransientModel):
    _name = 'hr.payslip.employees'
    _description = 'Generate payslips for all selected employees'

    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employees')

    def compute_sheet(self):
        active_id = self.env.context.get('active_id')
        if not active_id:
            raise UserError(_("Generate the payslips from a payslip batch."))
        if not self.employee_ids:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))
        self.env['hr.payslip.run'].browse(active_id)._generate_payslips(self.employee_ids)
        return {'type': 'ir.actions.act_window_close'}
