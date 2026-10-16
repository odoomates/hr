from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrExit(models.Model):
    _inherit = 'hr.exit'

    settlement_payslip_id = fields.Many2one('hr.payslip', string='Final Settlement', readonly=True, copy=False,
                                            groups='hr.group_hr_user')
    encashment_days = fields.Float(string='Unused Time Off (Days)', compute='_compute_encashment',
                                   groups='hr.group_hr_user', digits=(16, 2))
    encashment_amount = fields.Monetary(string='Time Off Paid Out', compute='_compute_encashment',
                                        groups='hr.group_hr_user', currency_field='currency_id')

    @api.depends('employee_id', 'last_working_day')
    def _compute_encashment(self):
        for exit_ in self:
            exit_.encashment_days = exit_._hr_encashment_days()
            exit_.encashment_amount = exit_._hr_encashment_amount()

    def _hr_encashment_days(self):
        """ The days left on the allocations of the time off paid out at the exit, on the last working day. """
        self.ensure_one()
        types = self.env['hr.work.entry.type'].sudo().search([('encashable', '=', True)])
        employee = self.employee_id.sudo()
        if not types or not employee or not self.last_working_day:
            return 0.0
        consumed = employee._get_consumed_leaves(types, self.last_working_day)[0]
        days = 0.0
        for allocations in consumed.get(employee, {}).values():
            for allocation, data in allocations.items():
                if allocation:
                    days += data.get('days_virtual_remaining_leaves', 0.0)
        return max(days, 0.0)

    def _hr_encashment_amount(self):
        """ A day of time off is paid the daily wage: the monthly wage over the days per month of the payroll. """
        self.ensure_one()
        employee = self.employee_id.sudo()
        if not employee or not self.last_working_day:
            return 0.0
        version = employee._get_version(self.last_working_day) or employee.version_id
        days = self.company_id.om_payroll_month_days or 30.0
        return self.company_id.currency_id.round(self._hr_encashment_days() * version.wage / days)

    def action_final_settlement(self):
        """ The payslip of the last month, up to the last working day, with what the exit pays and deducts. """
        self.ensure_one()
        if not self.env.user.has_group('om_hr_payroll.group_hr_payroll_user'):
            raise UserError(_('Only the payroll officers create the final settlement.'))
        if self.state not in ('approved', 'done'):
            raise UserError(_('The final settlement of %s waits for the exit to be approved.', self.name))
        if self.settlement_payslip_id and self.settlement_payslip_id.state != 'cancel':
            return self.action_open_settlement()
        Payslip = self.env['hr.payslip']
        date_from = self.last_working_day.replace(day=1)
        values = Payslip.onchange_employee_id(date_from, self.last_working_day, self.employee_id.id)['value']
        if not values.get('version_id'):
            raise UserError(_('%s has no contract running in the last month.', self.employee_id.name))
        payslip = Payslip.create({
            'employee_id': self.employee_id.id,
            'date_from': date_from,
            'date_to': self.last_working_day,
            'name': _('Final Settlement of %s', self.employee_id.name),
            'company_id': values.get('company_id'),
            'version_id': values['version_id'],
            'struct_id': values.get('struct_id'),
            'worked_days_line_ids': [(0, 0, line) for line in values.get('worked_days_line_ids', [])],
            'input_line_ids': [(0, 0, line) for line in values.get('input_line_ids', [])],
            'exit_id': self.id,
        })
        payslip.compute_sheet()
        self.settlement_payslip_id = payslip
        return self.action_open_settlement()

    def action_open_settlement(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'res_id': self.settlement_payslip_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }
