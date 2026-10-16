from odoo import api, fields, models


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    payslip_id = fields.Many2one('hr.payslip', string='Paid On', readonly=True, copy=False, index='btree_not_null',
                                    ondelete='set null', groups='om_hr_payroll.group_hr_payroll_user')

    @api.model
    def _overtime_domain(self):
        """ :return: the attendances that are overtime: what the time rules create, and the attendances of the
            types the time rules set the excess to, e.g. entered by hand. """
        excess_types = self.env['hr.time.rule'].sudo().with_context(active_test=False).search(
            [('work_entry_type_id', '!=', False)]).work_entry_type_id
        return ['|', ('time_rule_id', '!=', False), ('work_entry_type_id', 'in', excess_types.ids)]

    def _overtime_rate(self):
        """ :return: how much of the hourly wage an hour is paid, e.g. 1.5: the salary rate of the rule, else the
            rate of the type """
        self.ensure_one()
        if self.time_rule_id:
            return self.time_rule_id.amount_rate
        return self.work_entry_type_id.amount_rate
