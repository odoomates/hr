from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    def _get_partner_id(self, credit_account):
        """
        Get partner_id of slip line to use in account_move_line
        """
        # use partner of salary rule or fallback on employee's address
        register_partner_id = self.salary_rule_id.register_id.partner_id
        if register_partner_id:
            return register_partner_id.id
        account = self.salary_rule_id.account_credit if credit_account else self.salary_rule_id.account_debit
        # the employee for what they are owed or owe: the net salary, the items on a receivable or a payable account
        if (credit_account and self.category_id.code == 'NET') or \
                account.account_type in ('asset_receivable', 'liability_payable'):
            return self.slip_id.employee_id.work_contact_id.id
        return False


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    date = fields.Date(
        'Date Account', help="Keep empty to use the period of the validation(Payslip) date."
    )
    journal_id = fields.Many2one(
        'account.journal', 'Salary Journal', required=True,
        default=lambda self: self.env['account.journal'].search([('type', '=', 'general')], limit=1)
    )
    move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        if 'journal_id' in self.env.context:
            for vals in vals_list:
                vals['journal_id'] = self.env.context.get('journal_id')
        return super(HrPayslip, self).create(vals_list)

    @api.onchange('contract_id')
    def onchange_contract(self):
        super(HrPayslip, self).onchange_contract()
        self.journal_id = self.contract_id.journal_id.id or (not self.contract_id and self.default_get(['journal_id'])['journal_id'])

    def _remove_accounting_entry(self):
        moves = self.mapped('move_id')
        moves.filtered(lambda x: x.state == 'posted').button_cancel()
        moves.unlink()

    def action_payslip_cancel(self):
        self._remove_accounting_entry()
        return super(HrPayslip, self).action_payslip_cancel()

    def action_payslip_draft(self):
        # confirmed again, the payslip posts a new entry
        self._remove_accounting_entry()
        return super(HrPayslip, self).action_payslip_draft()

    def action_payslip_done(self):
        res = super(HrPayslip, self).action_payslip_done()

        for slip in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            date = slip.date or slip.date_to
            currency = slip.company_id.currency_id

            name = _('Payslip of %s') % (slip.employee_id.name)
            move_dict = {
                'narration': name,
                'ref': slip.number,
                'journal_id': slip.journal_id.id,
                'date': date,
            }
            # the debit and the credit side may legitimately come from two different
            # salary rules, so require the accounts across the whole payslip rather
            # than on any single rule (see PR #135)
            payslip_rules = slip.details_by_salary_rule_category.salary_rule_id
            if not (payslip_rules.account_debit and payslip_rules.account_credit):
                raise UserError(_('Missing Debit Or Credit Account in Salary Rule'))
            for line in slip.details_by_salary_rule_category:
                amount = currency.round(slip.credit_note and -line.total or line.total)
                if currency.is_zero(amount):
                    continue

                debit_account_id = line.salary_rule_id.account_debit.id
                credit_account_id = line.salary_rule_id.account_credit.id
                # the analytic account of the rule, else the one of the contract
                analytic_account = line.salary_rule_id.analytic_account_id or line.contract_id.analytic_account_id
                analytic_distribution = {analytic_account.id: 100} if analytic_account else {}
                # if not debit_account_id or not credit_account_id:
                #     raise UserError(_('Missing Debit Or Credit Account in salary rule: "%s" !') % (
                #         line.salary_rule_id))
                if debit_account_id:
                    debit_line = (0, 0, {
                        'name': line.name,
                        'partner_id': line._get_partner_id(credit_account=False),
                        'account_id': debit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amount > 0.0 and amount or 0.0,
                        'credit': amount < 0.0 and -amount or 0.0,
                        'analytic_distribution': analytic_distribution,
                        'tax_line_id': line.salary_rule_id.account_tax_id.id,
                    })
                    line_ids.append(debit_line)
                    debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if credit_account_id:
                    credit_line = (0, 0, {
                        'name': line.name,
                        'partner_id': line._get_partner_id(credit_account=True),
                        'account_id': credit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amount < 0.0 and -amount or 0.0,
                        'credit': amount > 0.0 and amount or 0.0,
                        'analytic_distribution': analytic_distribution,
                        'tax_line_id': line.salary_rule_id.account_tax_id.id,
                    })
                    line_ids.append(credit_line)
                    credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

            if not line_ids:
                # nothing to post: an entry without lines cannot be posted
                continue

            if currency.compare_amounts(credit_sum, debit_sum) == -1:
                acc_id = slip.journal_id.default_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (slip.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': 0.0,
                    'credit': currency.round(debit_sum - credit_sum),
                })
                line_ids.append(adjust_credit)

            elif currency.compare_amounts(debit_sum, credit_sum) == -1:
                acc_id = slip.journal_id.default_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (slip.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': currency.round(credit_sum - debit_sum),
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            slip.write({'move_id': move.id, 'date': date})
            move.action_post()
        return res


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    account_tax_id = fields.Many2one('account.tax', 'Tax')
    account_debit = fields.Many2one('account.account', 'Debit Account', domain=[('deprecated', '=', False)])
    account_credit = fields.Many2one('account.account', 'Credit Account', domain=[('deprecated', '=', False)])


class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    journal_id = fields.Many2one('account.journal', 'Salary Journal')


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    journal_id = fields.Many2one(
        'account.journal', 'Salary Journal', required=True,
        default=lambda self: self.env['account.journal'].search([('type', '=', 'general')], limit=1)
    )

    def _generate_payslips(self, employees, skip_errors=False):
        # the payslips generated, from the wizard or the monthly batch, take the salary journal of the batch
        return super(HrPayslipRun, self.with_context(journal_id=self.journal_id.id))._generate_payslips(
            employees, skip_errors=skip_errors)

    @api.model
    def _monthly_batch_values(self, company, date_start, date_end):
        values = super()._monthly_batch_values(company, date_start, date_end)
        journal = self.env['account.journal'].search([('type', '=', 'general'), ('company_id', '=', company.id)],
                                                     limit=1)
        if not journal:
            raise UserError(_('%s has no miscellaneous journal for the salaries.') % company.name)
        values['journal_id'] = journal.id
        return values
