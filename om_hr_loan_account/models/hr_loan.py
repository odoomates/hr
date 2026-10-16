from odoo import _, api, fields, models
from odoo.exceptions import UserError


class OmHrLoan(models.Model):
    _inherit = 'om.hr.loan'

    payment_ids = fields.One2many('account.payment', 'om_loan_id', string='Payments', readonly=True)
    payment_count = fields.Integer(compute='_compute_payment_count')

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for loan in self:
            loan.payment_count = len(loan.payment_ids)

    def _om_accounting(self):
        """ :return: the loan account and the payment journal of the type of the loan, in its company, or two
            empty records when the loan type is not set up for accounting """
        self.ensure_one()
        loan_type = self.type_id.with_company(self.company_id)
        return loan_type.account_id, loan_type.journal_id

    def _om_pay(self, amount, payment_type, memo, date=None):
        """ A posted payment between the company and the employee on the loan account, matched with the other
            entries of the employee on it. """
        self.ensure_one()
        account, journal = self._om_accounting()
        if not account or not journal:
            return self.env['account.payment']
        partner = self.employee_id.sudo().work_contact_id
        if not partner:
            raise UserError(_('%s has no contact to pay.', self.employee_id.name))
        method = journal._get_available_payment_method_lines(payment_type)[:1]
        if not method:
            raise UserError(_('The journal %s has no payment method for this payment.', journal.name))
        payment = self.env['account.payment'].sudo().create({
            'payment_type': payment_type,
            'partner_type': 'customer',
            'partner_id': partner.id,
            'amount': amount,
            'date': date or fields.Date.context_today(self),
            'memo': memo,
            'journal_id': journal.id,
            'payment_method_line_id': method.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'destination_account_id': account.id,
            'om_loan_id': self.id,
        })
        payment.action_post()
        self._om_reconcile()
        return payment

    def _om_reconcile(self):
        """ Match what each employee owes on the loan account with what they repaid. """
        for loan in self:
            account, _journal = loan._om_accounting()
            partner = loan.employee_id.sudo().work_contact_id
            if not account or not partner:
                continue
            lines = self.env['account.move.line'].sudo().search([
                ('account_id', '=', account.id), ('partner_id', '=', partner.id),
                ('reconciled', '=', False), ('parent_state', '=', 'posted'), ('company_id', '=', loan.company_id.id),
            ])
            if lines.filtered(lambda line: line.balance > 0) and lines.filtered(lambda line: line.balance < 0):
                lines.reconcile()

    def action_disburse(self):
        result = super().action_disburse()
        for loan in self:
            loan._om_pay(loan.amount, 'outbound', _('%s paid out', loan.name), loan.date_disbursed)
        return result

    def action_settle(self):
        due = {loan: sum(loan.line_ids.filtered(lambda line: line.state == 'to_pay').mapped('amount'))
               for loan in self}
        result = super().action_settle()
        for loan, amount in due.items():
            if loan.currency_id.compare_amounts(amount, 0) > 0:
                loan._om_pay(amount, 'inbound', _('%s settled', loan.name))
        return result

    def action_open_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payments of %s', self.name),
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('om_loan_id', '=', self.id)],
            'context': {'create': False},
        }


class OmHrLoanLine(models.Model):
    _inherit = 'om.hr.loan.line'

    def action_mark_paid(self):
        result = super().action_mark_paid()
        for line in self:
            line.loan_id._om_pay(line.amount, 'inbound', _('%(loan)s: installment of %(month)s', loan=line.loan_id.name,
                                                           month=line.date.strftime('%B %Y')))
        return result


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    om_loan_id = fields.Many2one('om.hr.loan', string='Employee Loan', readonly=True, copy=False,
                                 index='btree_not_null')
