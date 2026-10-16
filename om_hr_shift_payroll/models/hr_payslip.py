from odoo import api, fields, models

SHIFT_CODE = 'SHIFT_ALW'


class HrShift(models.Model):
    _inherit = 'hr.shift'

    payslip_id = fields.Many2one('hr.payslip', string='Allowance Paid On', readonly=True, copy=False,
                                    index='btree_not_null', ondelete='set null', check_company=True)
    allowance = fields.Monetary(related='template_id.allowance', string='Allowance')
    currency_id = fields.Many2one(related='template_id.currency_id')

    def _on_time_off(self):
        """ :return: the shifts the employee does not work: on time off or a public holiday the whole shift """
        off = self.browse()
        for shift in self:
            leaves = self.env['resource.calendar.leaves'].sudo().search([
                ('date_from', '<=', shift.start), ('date_to', '>=', shift.stop),
                '|', ('resource_id', '=', shift.employee_id.resource_id.id),
                '&', ('resource_id', '=', False), ('company_id', 'in', [shift.company_id.id, False])])
            if leaves.filtered(lambda time_off: time_off.resource_id or not time_off.calendar_id
                               or time_off.calendar_id == shift.employee_id.sudo().roster_calendar_id):
                off |= shift
        return off


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    @api.model
    def _hr_shift_add_to_base_structure(self):
        """ The structures created from now on pay the shift allowances: the base structure gets the rule. """
        structure = self.env.ref('om_hr_payroll.structure_base', raise_if_not_found=False)
        rule = self.env.ref('om_hr_shift_payroll.hr_rule_shift_allowance', raise_if_not_found=False)
        if structure and rule and rule not in structure.rule_ids:
            structure.rule_ids = [(4, rule.id)]


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    shift_ids = fields.One2many('hr.shift', 'payslip_id', string='Shift Allowances')

    def compute_sheet(self):
        self._shift_sync()
        return super().compute_sheet()

    def _shift_sync(self):
        """ Give each payslip the allowances of the published shifts of its employee up to the end of its period
            not paid yet, those published late included, the shifts on time off left out, as the input SHIFT_ALW. """
        Shift = self.env['hr.shift'].sudo()
        for payslip in self.filtered(lambda p: not p.credit_note and p.state not in ('done', 'cancel')):
            Shift.search([('payslip_id', '=', payslip.id)]).payslip_id = False
            shifts = Shift.search([
                ('employee_id', '=', payslip.employee_id.id), ('state', '=', 'published'),
                ('date', '<=', payslip.date_to), ('template_id.allowance', '>', 0),
                '|', ('payslip_id', '=', False), ('payslip_id.state', '=', 'cancel'),
            ])
            shifts -= shifts._on_time_off()
            shifts.payslip_id = payslip
            amount = payslip.company_id.currency_id.round(sum(shifts.mapped('allowance')))
            name = self.env._('Shift Allowances (%s shifts)', len(shifts))
            version = payslip.version_id or self.env['hr.version'].browse(
                self.get_versions(payslip.employee_id, payslip.date_from, payslip.date_to)[:1])
            inputs = payslip.input_line_ids.filtered(lambda line: line.code == SHIFT_CODE)
            if inputs:
                inputs[0].write({'amount': amount, 'name': name})
                inputs[1:].unlink()
            elif amount and version:
                payslip.input_line_ids = [(0, 0, {
                    'name': name, 'code': SHIFT_CODE, 'amount': amount, 'version_id': version.id, 'sequence': 85,
                })]

    def _shift_release(self):
        """ The allowances of the payslips are to pay again: the payslip is cancelled or refunded. """
        self.env['hr.shift'].sudo().search(
            [('payslip_id', 'in', self.filtered(lambda p: not p.credit_note).ids)]).payslip_id = False

    def action_payslip_cancel(self):
        self._shift_release()
        return super().action_payslip_cancel()

    def refund_sheet(self):
        self._shift_release()
        return super().refund_sheet()
