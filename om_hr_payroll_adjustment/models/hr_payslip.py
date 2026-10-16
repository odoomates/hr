from odoo import fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    adjustment_line_ids = fields.One2many('hr.payroll.adjustment.line', 'payslip_id',
                                             string='Payroll Adjustments', readonly=True)

    def _adjustment_lines(self):
        return self.env['hr.payroll.adjustment.line'].sudo().search([('payslip_id', 'in', self.ids)])

    def _adjustment_settles_all(self):
        """ The final settlement of an exit takes everything due on the types settled at exit. """
        self.ensure_one()
        return bool('exit_id' in self._fields and self.exit_id)

    def _adjustment_version(self):
        self.ensure_one()
        return self.version_id or self.env['hr.version'].browse(
            self.get_versions(self.employee_id, self.date_from, self.date_to)[:1])

    def _adjustment_gross(self):
        """ :return: the gross of the payslip as last computed """
        self.ensure_one()
        lines = self.line_ids.filtered(lambda line: line.category_id.code == 'GROSS')
        if not lines:
            lines = self.line_ids.filtered(lambda line: line.category_id.code in ('BASIC', 'ALW'))
        return sum(lines.mapped('total'))

    def _adjustment_sync(self):
        """ Give each payslip the adjustment lines due by the end of its period and not taken yet, those of earlier
            months included, as one input per adjustment type, read by the rule of the type. """
        Line = self.env['hr.payroll.adjustment.line'].sudo()
        Adjustment = self.env['hr.payroll.adjustment'].sudo()
        codes = set(self.env['hr.payroll.adjustment.type'].sudo().with_context(active_test=False)
                    .search([('code', '!=', False)]).mapped('code'))
        for payslip in self.filtered(lambda p: not p.credit_note and p.state not in ('done', 'cancel')):
            Line.search([('payslip_id', '=', payslip.id), ('state', '=', 'to_pay')]).payslip_id = False
            settles = payslip._adjustment_settles_all()
            adjustments = Adjustment.search([('employee_id', '=', payslip.employee_id.id), ('state', '=', 'running'),
                                             ('date_start', '<=', payslip.date_to)])
            # a percentage until a total gets the line of the month of the payslip when it needs one
            month = payslip.date_to.replace(day=1)
            for adjustment in adjustments.filtered(
                    lambda a: a.recurrence == 'total' and a.amount_type == 'percent'
                    and not a.line_ids.filtered(lambda line: line.date == month)):
                Line.create({'adjustment_id': adjustment.id, 'date': month})
            domain = [
                ('adjustment_id', 'in', adjustments.ids),
                ('state', '=', 'to_pay'),
                '|', ('payslip_id', '=', False), ('payslip_id.state', '=', 'cancel'),
            ]
            if settles:
                domain += ['|', ('date', '<=', payslip.date_to), ('type_id.settle_at_exit', '=', True)]
            else:
                domain.append(('date', '<=', payslip.date_to))
            due = Line.search(domain)
            due.payslip_id = payslip
            payslip._adjustment_set_amounts(due, settles)
            payslip._adjustment_set_inputs(due, codes)

    def _adjustment_set_amounts(self, lines, settles):
        """ The amounts of the percentages, of the wage or of the gross; a total is never exceeded, and the final
            settlement takes all that is left of a total settled at exit. """
        self.ensure_one()
        wage = self._adjustment_version().wage
        gross = self._adjustment_gross()
        for adjustment in lines.adjustment_id:
            currency = adjustment.currency_id
            left = None
            if adjustment.recurrence == 'total':
                left = adjustment.total_amount - sum(
                    adjustment.line_ids.filtered(lambda line: line.state == 'paid').mapped('amount'))
            for line in lines.filtered(lambda item: item.adjustment_id == adjustment).sorted('date'):
                amount = line.amount
                if adjustment.amount_type == 'percent':
                    base = gross if adjustment.percent_base == 'gross' else wage
                    amount = currency.round(base * adjustment.percent / 100)
                if left is not None:
                    if settles and adjustment.type_id.settle_at_exit and adjustment.amount_type == 'percent':
                        amount = left
                    amount = max(min(amount, left), 0.0)
                    left -= amount
                if currency.compare_amounts(amount, line.amount):
                    line.amount = amount

    def _adjustment_set_inputs(self, lines, codes):
        self.ensure_one()
        by_type = {}
        for line in lines:
            by_type.setdefault(line.type_id, 0.0)
            by_type[line.type_id] += line.amount
        amounts = {adjustment_type.code: (adjustment_type, amount) for adjustment_type, amount in by_type.items()}
        version = self._adjustment_version()
        for code in codes:
            inputs = self.input_line_ids.filtered(lambda line: line.code == code)
            adjustment_type, amount = amounts.get(code, (False, 0.0))
            if not amount:
                inputs.unlink()
            elif inputs:
                inputs[0].amount = amount
                inputs[1:].unlink()
            elif version:
                self.input_line_ids = [(0, 0, {
                    'name': adjustment_type.name, 'code': code, 'amount': amount, 'version_id': version.id,
                    'sequence': 95,
                })]

    def compute_sheet(self):
        self._adjustment_sync()
        result = super().compute_sheet()
        # a percentage of the gross needs the gross: the payslip computes again, with it
        again = self.filtered(lambda payslip: payslip._adjustment_lines().filtered(
            lambda line: line.state == 'to_pay' and line.adjustment_id.amount_type == 'percent'
            and line.adjustment_id.percent_base == 'gross'))
        if again:
            again._adjustment_sync()
            super(HrPayslip, again).compute_sheet()
        return result

    def action_payslip_done(self):
        result = super().action_payslip_done()
        for payslip in self.filtered(lambda p: p.state == 'done' and not p.credit_note):
            payslip._adjustment_lines().filtered(lambda line: line.state == 'to_pay')._mark_paid(
                self.env._('Taken by %s', payslip.number or payslip.name), date=payslip.date_to)
        return result

    def action_payslip_draft(self):
        self._adjustment_release(keep=True)
        return super().action_payslip_draft()

    def action_payslip_cancel(self):
        self._adjustment_release()
        return super().action_payslip_cancel()

    def refund_sheet(self):
        self._adjustment_release()
        return super().refund_sheet()

    def _adjustment_release(self, keep=False):
        """ The lines of the payslips are due again: the payslip is cancelled, refunded, or set back to draft, in
            which case it keeps them, to take them when confirmed again. """
        lines = self.filtered(lambda p: not p.credit_note)._adjustment_lines()
        values = {'state': 'to_pay', 'date_paid': False, 'note': False}
        if not keep:
            values['payslip_id'] = False
        adjustments = lines.adjustment_id
        lines.write(values)
        adjustments.filtered(lambda adjustment: adjustment.state == 'done').write({'state': 'running'})
