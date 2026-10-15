from odoo import _, fields, models

OVERTIME_CODE = 'OVERTIME'


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    om_overtime_ids = fields.One2many('hr.attendance', 'om_payslip_id', string='Overtime')
    om_overtime_hours = fields.Float(string='Overtime Hours', compute='_compute_om_overtime_hours')

    def _compute_om_overtime_hours(self):
        for payslip in self:
            payslip.om_overtime_hours = sum(payslip.sudo().om_overtime_ids.mapped('worked_hours'))

    def compute_sheet(self):
        self._om_overtime_sync()
        return super().compute_sheet()

    def _om_overtime_hourly_wage(self, version):
        """ :return: the hourly wage the overtime is paid from: the hourly wage of an hourly contract, else the
            monthly wage / the days per month of the payroll settings / the hours per day of the working schedule """
        self.ensure_one()
        return self._om_wage_rates(version)['hourly_wage']

    def _om_overtime_sync(self):
        """ Give each payslip the validated overtime of its employee up to the end of its period not paid yet, that
            validated late included, as the input OVERTIME read by the overtime rule.

            The time rules create overtime only from validated attendances, so a validated overtime is approved.
            An overtime whose attendance changed since (stale) waits for the rules to compute it again. """
        Attendance = self.env['hr.attendance'].sudo()
        for payslip in self.filtered(lambda p: not p.credit_note and p.state not in ('done', 'cancel')):
            Attendance.search([('om_payslip_id', '=', payslip.id)]).om_payslip_id = False
            version = payslip.version_id or self.env['hr.version'].browse(
                self.get_versions(payslip.employee_id, payslip.date_from, payslip.date_to)[:1])
            overtime = Attendance.search([
                ('employee_id', '=', payslip.employee_id.id),
                ('state', '=', 'validated'),
                ('source_stale', '=', False),
                ('date', '<=', payslip.date_to),
                '|', ('om_payslip_id', '=', False), ('om_payslip_id.state', '=', 'cancel'),
            ] + Attendance._om_overtime_domain())
            overtime.om_payslip_id = payslip
            hourly = payslip._om_overtime_hourly_wage(version) if version else 0.0
            amount = payslip.company_id.currency_id.round(
                sum(attendance.worked_hours * hourly * attendance._om_overtime_rate() for attendance in overtime))
            name = _('Overtime (%s h)', round(sum(overtime.mapped('worked_hours')), 2))
            inputs = payslip.input_line_ids.filtered(lambda line: line.code == OVERTIME_CODE)
            if inputs:
                inputs[0].write({'amount': amount, 'name': name})
                inputs[1:].unlink()
            elif amount and version:
                payslip.input_line_ids = [(0, 0, {
                    'name': name, 'code': OVERTIME_CODE, 'amount': amount, 'version_id': version.id, 'sequence': 80,
                })]

    def _om_overtime_release(self):
        """ The overtime of the payslips is to pay again: the payslip is cancelled or refunded. """
        self.env['hr.attendance'].sudo().search(
            [('om_payslip_id', 'in', self.filtered(lambda p: not p.credit_note).ids)]).om_payslip_id = False

    def action_payslip_cancel(self):
        self._om_overtime_release()
        return super().action_payslip_cancel()

    def refund_sheet(self):
        self._om_overtime_release()
        return super().refund_sheet()
