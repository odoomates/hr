from odoo import _, models

LOAN_CODE = 'LOAN'


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _hr_loan_lines(self):
        return self.env['hr.loan.line'].sudo().search([('payslip_id', 'in', self.ids)])

    def _hr_loan_sync(self):
        """ Give each payslip the installments due by the end of its period and not deducted yet, those of earlier
            months included, as the input LOAN read by the loan rule. """
        Line = self.env['hr.loan.line'].sudo()
        for payslip in self.filtered(lambda p: not p.credit_note and p.state not in ('done', 'cancel')):
            Line.search([('payslip_id', '=', payslip.id), ('state', '=', 'to_pay')]).payslip_id = False
            domain = [
                ('employee_id', '=', payslip.employee_id.id),
                ('loan_id.state', '=', 'running'),
                ('state', '=', 'to_pay'),
                '|', ('payslip_id', '=', False), ('payslip_id.state', '=', 'cancel'),
            ]
            if not payslip._hr_loan_settles_all():
                domain.append(('date', '<=', payslip.date_to))
            due = Line.search(domain)
            due.payslip_id = payslip
            amount = sum(due.mapped('amount'))
            inputs = payslip.input_line_ids.filtered(lambda line: line.code == LOAN_CODE)
            if inputs:
                inputs[0].amount = amount
                inputs[1:].unlink()
            elif amount:
                version = payslip.version_id or self.env['hr.version'].browse(
                    self.get_versions(payslip.employee_id, payslip.date_from, payslip.date_to)[:1])
                if version:
                    payslip.input_line_ids = [(0, 0, {
                        'name': _('Loan Installments'), 'code': LOAN_CODE, 'amount': amount,
                        'version_id': version.id, 'sequence': 90,
                    })]

    def _hr_loan_settles_all(self):
        """ The final settlement of an exit deducts every installment still due. """
        self.ensure_one()
        return bool('exit_id' in self._fields and self.exit_id)

    def compute_sheet(self):
        self._hr_loan_sync()
        return super().compute_sheet()

    def action_payslip_done(self):
        result = super().action_payslip_done()
        for payslip in self.filtered(lambda p: p.state == 'done' and not p.credit_note):
            payslip._hr_loan_lines().filtered(lambda l: l.state == 'to_pay')._mark_paid(
                _('Deducted from %s', payslip.number or payslip.name), date=payslip.date_to)
        return result

    def action_payslip_draft(self):
        self._hr_loan_release(keep=True)
        return super().action_payslip_draft()

    def action_payslip_cancel(self):
        self._hr_loan_release()
        return super().action_payslip_cancel()

    def refund_sheet(self):
        self._hr_loan_release()
        return super().refund_sheet()

    def _hr_loan_release(self, keep=False):
        """ The installments of the payslips are due again: the payslip is cancelled, refunded, or set back to
            draft, in which case it keeps them, to deduct them when confirmed again. """
        lines = self.filtered(lambda p: not p.credit_note)._hr_loan_lines()
        values = {'state': 'to_pay', 'date_paid': False, 'note': False}
        if not keep:
            values['payslip_id'] = False
        loans = lines.loan_id
        lines.write(values)
        loans.filtered(lambda loan: loan.state == 'paid').write({'state': 'running'})
