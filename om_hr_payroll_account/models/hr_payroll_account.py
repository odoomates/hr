from collections import defaultdict

from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError, ValidationError

PAYMENT_STATES = [
    ('not_paid', 'Not Paid'),
    ('in_payment', 'In Payment'),
    ('partial', 'Partially Paid'),
    ('paid', 'Paid'),
    ('reversed', 'Reversed'),
]


def _default_salary_journal(records):
    # the payroll users may have no accounting rights: only the journal of the company is looked up
    company = records.env.company
    journal = records.env['account.journal'].sudo().search([
        ('type', '=', 'general'), ('company_id', '=', company.id),
    ], limit=1)
    return journal.id


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    # a payslip line is the line of one company: it keeps the accounts of its rule, as they were computed,
    # where the model of the salary rules holds one value per company
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', company_dependent=False,
                                          check_company=True)
    account_tax_id = fields.Many2one('account.tax', 'Tax', company_dependent=False, check_company=True)
    account_debit = fields.Many2one('account.account', 'Debit Account', company_dependent=False)
    account_credit = fields.Many2one('account.account', 'Credit Account', company_dependent=False)

    def _get_partner_id(self, credit_account):
        """ :return: the partner of the journal item of the line: the partner of the contribution register of its
        rule, else the employee for what they are owed or owe: the net salary, and the items on a receivable or a
        payable account, e.g. a salary advance recovered, so they are reconciled per employee. """
        register_partner = self.salary_rule_id.register_id.partner_id
        if register_partner:
            return register_partner.id
        rule = self.salary_rule_id
        account = rule.account_credit if credit_account else rule.account_debit
        if (credit_account and self.category_id.code == 'NET') \
                or account.account_type in ('asset_receivable', 'liability_payable'):
            return self.slip_id.employee_id.sudo().work_contact_id.id
        return False

    def _get_tax_values(self, account):
        """ :return: the values making the journal item of the line on that account the tax line of the tax of
        its rule: the repartition line of the tax on that account, and its tax grids, for the tax reports. """
        tax = self.salary_rule_id.account_tax_id.sudo()
        repartition = tax.invoice_repartition_line_ids.filtered(
            lambda line: line.repartition_type == 'tax' and line.account_id == account)[:1]
        if not repartition:
            return {'tax_repartition_line_id': False, 'tax_tag_ids': []}
        return {'tax_repartition_line_id': repartition.id, 'tax_tag_ids': [Command.set(repartition.tag_ids.ids)]}


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    date = fields.Date(
        'Date Account', help="Keep empty to use the period of the validation(Payslip) date."
    )
    journal_id = fields.Many2one(
        'account.journal', 'Salary Journal', required=True, default=_default_salary_journal,
        domain="[('company_id', '=', company_id)]", check_company=True,
    )
    move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True, copy=False, check_company=True)
    payment_ids = fields.Many2many(
        'account.payment', 'hr_payslip_account_payment_rel', 'payslip_id', 'payment_id', string='Payments',
        readonly=True, copy=False, groups='account.group_account_invoice,account.group_account_readonly',
    )
    payment_count = fields.Integer(
        compute='_compute_payment_count', groups='account.group_account_invoice,account.group_account_readonly',
    )
    payment_state = fields.Selection(
        PAYMENT_STATES, string='Payment Status', compute='_compute_payment_state', store=True, readonly=True,
        copy=False, index=True, default='not_paid',
        help="Paid: the net salary is matched with a payment. In Payment: a payment is registered but not "
             "matched yet. Reversed: the payslip was refunded before being paid.",
    )
    paid = fields.Boolean(compute='_compute_paid', store=True, readonly=False)

    def _get_salary_payable_lines(self):
        """ :return: the journal items of the entry for what is owed to the employee: the net salary, credited on the
        credit account of the net rule, or else on a payable account. A refund owes it back: its items are debits. """
        self.ensure_one()
        move_lines = self.move_id.line_ids
        slip = self.with_company(self.company_id)
        accounts = slip.line_ids.filtered(lambda line: line.category_id.code == 'NET').salary_rule_id.account_credit
        lines = move_lines.filtered(lambda line: line.account_id in accounts)
        if not lines:
            lines = move_lines.filtered(lambda line: line.account_id.account_type == 'liability_payable')
        return lines.filtered(lambda line: line.balance > 0 if self.credit_note else line.balance < 0)

    def _can_register_payment(self):
        self.ensure_one()
        return (self.state == 'done' and not self.credit_note and self.move_id.state == 'posted'
                and self.payment_state in ('not_paid', 'partial'))

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for slip in self:
            slip.payment_count = len(slip.payment_ids)

    @api.depends('state', 'credit_note', 'move_id.state', 'move_id.line_ids.amount_residual',
                 'move_id.line_ids.reconciled', 'payment_ids.state', 'payment_ids.move_id',
                 'payment_ids.is_matched')
    def _compute_payment_state(self):
        in_payment_state = self.env['account.move']._get_invoice_in_payment_state()
        for slip in self:
            lines = slip.sudo()._get_salary_payable_lines() if slip.move_id else None
            if slip.state != 'done' or not lines or slip.move_id.state != 'posted':
                slip.payment_state = 'not_paid'
                continue
            currency = slip.company_id.currency_id
            residual = sum(lines.mapped('amount_residual'))
            if currency.is_zero(residual):
                partials = lines.matched_debit_ids | lines.matched_credit_ids
                counterparts = (partials.debit_move_id | partials.credit_move_id).move_id - slip.move_id
                payments = counterparts.origin_payment_id
                if not payments and not counterparts.statement_line_id:
                    slip.payment_state = 'reversed'
                elif payments and not all(payment.is_matched for payment in payments):
                    slip.payment_state = in_payment_state
                else:
                    slip.payment_state = 'paid'
            elif currency.compare_amounts(abs(residual), abs(sum(lines.mapped('balance')))) < 0:
                slip.payment_state = 'partial'
            elif slip.sudo().payment_ids.filtered(lambda payment: not payment.move_id
                                                   and payment.state in ('paid', 'reconciled')):
                # a payment without entry is matched with the bank statement later
                slip.payment_state = 'in_payment'
            else:
                slip.payment_state = 'not_paid'

    @api.depends('payment_state')
    def _compute_paid(self):
        for slip in self:
            slip.paid = slip.payment_state in ('in_payment', 'paid')

    def action_register_payment(self):
        payslips = self.filtered(lambda slip: slip._can_register_payment())
        if not payslips:
            raise UserError(_('Nothing to pay: only the confirmed payslips with a posted entry that are not paid yet '
                              'can be paid. The refunds are not paid.'))
        return {
            'name': _('Pay Salaries'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.payment.register',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_payslip_ids': payslips.ids},
        }

    def action_open_payments(self):
        self.ensure_one()
        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(self.payment_ids) == 1:
            action.update({'view_mode': 'form', 'res_id': self.payment_ids.id})
        else:
            action.update({'view_mode': 'list,form', 'domain': [('id', 'in', self.payment_ids.ids)]})
        return action

    def refund_sheet(self):
        action = super().refund_sheet()
        # a payslip refunded before being paid owes nothing any more: its net salary is matched with the refund
        refunds = self.search(action['domain'])
        for original in self.filtered(lambda slip: slip.move_id and slip.payment_state == 'not_paid'):
            refund = refunds.filtered(lambda slip, original=original: slip.refunded_id == original)
            if not refund.move_id:
                continue
            lines = (original._get_salary_payable_lines() | refund._get_salary_payable_lines()).sudo()
            for account in lines.account_id.filtered('reconcile'):
                lines.filtered(lambda line: line.account_id == account and not line.reconciled).reconcile()
        return action

    @api.constrains('journal_id', 'company_id')
    def _check_journal_company(self):
        for slip in self:
            if slip.company_id and slip.journal_id.sudo().company_id != slip.company_id:
                raise ValidationError(_('The salary journal of the payslip %(payslip)s must belong to %(company)s.',
                                        payslip=slip.name or slip.number or '', company=slip.company_id.name))

    def _get_company_salary_journal(self):
        self.ensure_one()
        journal = self.version_id.journal_id
        if journal.sudo().company_id == self.company_id:
            return journal
        if self.journal_id.sudo().company_id == self.company_id:
            return self.journal_id
        return self.env['account.journal'].browse(_default_salary_journal(self.with_company(self.company_id)))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if self.env.context.get('journal_id'):
                vals.setdefault('journal_id', self.env.context['journal_id'])
            if not vals.get('journal_id') and vals.get('company_id'):
                # the default journal is the one of the company of the payslip, not of the current company
                journal_id = _default_salary_journal(self.with_company(vals['company_id']))
                if journal_id:
                    vals['journal_id'] = journal_id
        return super().create(vals_list)

    @api.onchange('version_id')
    def onchange_version(self):
        super().onchange_version()
        self.journal_id = self._get_company_salary_journal()

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee(self):
        res = super().onchange_employee()
        if self.company_id and self.journal_id.sudo().company_id != self.company_id:
            self.journal_id = self._get_company_salary_journal()
        return res

    def _remove_accounting_entry(self):
        """ Delete the accounting entries of the payslips, as they are cancelled or set back to draft.
        :return: the payslips whose entry stays because it is already reversed in Accounting. """
        reversed_slips = self.browse()
        for move in self.move_id:
            slips = self.filtered(lambda slip, move=move: slip.move_id == move)
            move = move.sudo()
            if move.reversal_move_ids.filtered(lambda reversal: reversal.state == 'posted'):
                # already cancelled in the books by a reversal: the entry stays
                reversed_slips |= slips
                continue
            paid = slips.filtered(lambda slip: slip.payment_state in ('in_payment', 'paid', 'partial'))
            if paid:
                raise UserError(_(
                    'The payslip %s is paid: cancel its payment in Accounting first.',
                    paid[0].number or paid[0].name or ''))
            # a consolidated entry posts the other payslips of the batch too
            others = self.sudo().search([('move_id', '=', move.id), ('id', 'not in', self.ids)])
            if others:
                raise UserError(_(
                    'The accounting entry %(entry)s also posts the payslips %(payslips)s: '
                    'cancel or set back to draft all of them together.',
                    entry=move.display_name,
                    payslips=', '.join(others.mapped(lambda slip: slip.number or slip.name or ''))))
            try:
                with self.env.cr.savepoint():
                    if move.state == 'posted':
                        move.button_draft()
                    move.unlink()
            except UserError as error:
                raise UserError(_(
                    'The accounting entry %(entry)s of the payslip %(payslip)s cannot be deleted: %(reason)s\n'
                    'Reverse the entry in Accounting, then cancel the payslip.',
                    entry=move.display_name, payslip=slips[0].number or slips[0].name or '',
                    reason=error.args[0],
                )) from error
        return reversed_slips

    def action_payslip_cancel(self):
        self._check_cancel()
        self._remove_accounting_entry()
        return super().action_payslip_cancel()

    def action_payslip_draft(self):
        self._check_set_to_draft()
        # confirmed again, the payslip posts a new entry: the reversed one is no longer its entry
        self._remove_accounting_entry().move_id = False
        return super().action_payslip_draft()

    def _check_salary_journal(self):
        """ :return: the salary journal of the payslip, read as superuser because the
        payroll users may have no accounting rights. """
        self.ensure_one()
        journal = self.journal_id.sudo()
        if journal.company_id != self.company_id:
            raise UserError(_('The salary journal %(journal)s does not belong to the company of the '
                              'payslip %(payslip)s.',
                              journal=journal.name, payslip=self.number or self.name or ''))
        return journal

    def _prepare_payslip_move_lines(self, date):
        """ :return: the journal items of this payslip, as a list of values. Shared by the
        entry of a single payslip and by the consolidated entry of a batch, so that the
        two can never drift apart. """
        self.ensure_one()
        # the accounts of the rules are the ones of the company of the payslip
        slip = self.with_company(self.company_id)
        currency = slip.company_id.currency_id
        # the debit and the credit side may legitimately come from two different
        # salary rules, so require the accounts across the whole payslip rather
        # than on any single rule (see PR #135)
        payslip_rules = slip.details_by_salary_rule_category.salary_rule_id
        if not (payslip_rules.account_debit and payslip_rules.account_credit):
            raise UserError(_('Missing Debit Or Credit Account in Salary Rule'))

        values = []
        for line in slip.details_by_salary_rule_category:
            amount = currency.round(slip.credit_note and -line.total or line.total)
            if currency.is_zero(amount):
                continue
            # the analytic account of the rule, else the one of the contract
            analytic_account = line.salary_rule_id.analytic_account_id or line.version_id.analytic_account_id
            analytic_distribution = {analytic_account.id: 100} if analytic_account else {}
            if line.salary_rule_id.account_debit:
                values.append({
                    'name': line.name,
                    'partner_id': line._get_partner_id(credit_account=False),
                    'account_id': line.salary_rule_id.account_debit.id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                    'analytic_distribution': analytic_distribution,
                    **line._get_tax_values(line.salary_rule_id.account_debit),
                })
            if line.salary_rule_id.account_credit:
                values.append({
                    'name': line.name,
                    'partner_id': line._get_partner_id(credit_account=True),
                    'account_id': line.salary_rule_id.account_credit.id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'analytic_distribution': analytic_distribution,
                    **line._get_tax_values(line.salary_rule_id.account_credit),
                })
        return values

    @api.model
    def _prepare_adjustment_move_line(self, journal, date, values, currency):
        """ :return: the values of the line balancing the entry, or None if it balances. """
        balance = currency.round(sum(vals['debit'] - vals['credit'] for vals in values))
        if currency.is_zero(balance):
            return None
        if not journal.default_account_id:
            raise UserError(
                _('The Expense Journal "%s" has not properly configured the Credit Account!') % journal.name
                if balance > 0.0 else
                _('The Expense Journal "%s" has not properly configured the Debit Account!') % journal.name)
        return {
            'name': _('Adjustment Entry'),
            'partner_id': False,
            'account_id': journal.default_account_id.id,
            'journal_id': journal.id,
            'date': date,
            'debit': balance < 0.0 and -balance or 0.0,
            'credit': balance > 0.0 and balance or 0.0,
        }

    @api.model
    def _merge_move_lines(self, values):
        """ Merge the journal items that are interchangeable: same label, account, partner,
        analytic distribution and tax. The partner is part of the key on purpose, so what is
        owed to each employee stays on its own line and can still be reconciled against the
        payment of that employee. """
        merged = {}
        for vals in values:
            key = (
                vals['name'],
                vals['account_id'],
                vals['partner_id'],
                tuple(sorted((vals['analytic_distribution'] or {}).items())),
                vals['tax_repartition_line_id'],
                tuple(sorted(vals['tax_tag_ids'][0][2])) if vals['tax_tag_ids'] else (),
            )
            if key in merged:
                merged[key]['debit'] += vals['debit']
                merged[key]['credit'] += vals['credit']
            else:
                merged[key] = dict(vals)
        result = []
        for vals in merged.values():
            # a journal item carries one side only
            balance = vals['debit'] - vals['credit']
            vals['debit'] = balance > 0.0 and balance or 0.0
            vals['credit'] = balance < 0.0 and -balance or 0.0
            result.append(vals)
        return result

    def _create_consolidated_move(self):
        """ Post one accounting entry for the whole set of payslips, instead of one per
        payslip. The payslips are grouped by company and by salary journal, because an
        entry belongs to a single company and a single journal. """
        groups = defaultdict(lambda: self.browse())
        for slip in self:
            slip._check_salary_journal()
            groups[(slip.company_id, slip.journal_id)] |= slip

        for (company, journal), slips in groups.items():
            currency = company.currency_id
            # the latest date of the group: an entry must not predate the payslips it posts
            date = max(slip.date or slip.date_to for slip in slips)
            values = []
            for slip in slips:
                values += slip._prepare_payslip_move_lines(date)
            values = self._merge_move_lines(values)
            if not values:
                continue
            adjustment = self._prepare_adjustment_move_line(journal.sudo(), date, values, currency)
            if adjustment:
                values.append(adjustment)

            batch = slips.payslip_run_id[:1]
            move_dict = {
                'narration': _('Consolidated payslip entry of %s', batch.name) if batch
                             else _('Consolidated payslip entry'),
                'ref': batch.name or ', '.join(slips.mapped('number')),
                'journal_id': journal.id,
                'company_id': company.id,
                'date': date,
                'line_ids': [(0, 0, vals) for vals in values],
            }
            # the payroll users may have no accounting rights: the entry follows the
            # configuration of the rules
            move = self.env['account.move'].sudo().with_company(company).create(move_dict)
            for slip in slips:
                slip.write({'move_id': move.id, 'date': slip.date or slip.date_to})
            move.action_post()

    def action_payslip_done(self):
        res = super().action_payslip_done()
        if self.env.context.get('hr_payroll_consolidated_move'):
            # the batch posts one entry for all its payslips once they are all done
            return res

        for slip in self:
            journal = slip._check_salary_journal()
            date = slip.date or slip.date_to
            currency = slip.company_id.currency_id
            values = slip._prepare_payslip_move_lines(date)
            if not values:
                # nothing to post: an entry without lines cannot be posted
                continue
            adjustment = self._prepare_adjustment_move_line(journal, date, values, currency)
            if adjustment:
                values.append(adjustment)
            move_dict = {
                'narration': _('Payslip of %s') % (slip.employee_id.name),
                'ref': slip.number,
                'journal_id': slip.journal_id.id,
                'company_id': slip.company_id.id,
                'date': date,
                'line_ids': [(0, 0, vals) for vals in values],
            }
            # the payroll users may have no accounting rights: the entry follows the
            # configuration of the rules
            move = self.env['account.move'].sudo().with_company(slip.company_id).create(move_dict)
            slip.write({'move_id': move.id, 'date': date})
            move.action_post()
        return res


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    # the default rules are shared by the companies: each company sets its own accounts on them
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', company_dependent=True,
                                          check_company=True)
    account_tax_id = fields.Many2one(
        'account.tax', 'Tax', company_dependent=True, check_company=True,
        help="The tax this rule computes: its journal item on the account of the tax is a tax line of the entry, "
             "with the tax grids of the tax, as shown in the tax reports.")
    account_debit = fields.Many2one('account.account', 'Debit Account', company_dependent=True)
    account_credit = fields.Many2one('account.account', 'Credit Account', company_dependent=True)


class HrVersion(models.Model):
    _inherit = 'hr.version'
    _description = 'Employee Contract'

    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', check_company=True)
    journal_id = fields.Many2one('account.journal', 'Salary Journal', check_company=True)

    @api.model
    def _company_checked_fields(self):
        return super()._company_checked_fields() + ['journal_id', 'analytic_account_id']


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    journal_id = fields.Many2one(
        'account.journal', 'Salary Journal', required=True, default=_default_salary_journal,
        domain="[('company_id', '=', company_id)]", check_company=True,
    )
    consolidated_move = fields.Boolean(
        'Consolidated Entry', copy=False,
        help="Post a single accounting entry for the whole batch instead of one entry per "
             "payslip. The journal items of the same salary rule are added up, while what is "
             "owed to each employee stays on its own line so that it can still be reconciled "
             "with the payment of that employee.",
    )
    has_payslips_to_pay = fields.Boolean(compute='_compute_payments')
    payment_count = fields.Integer(
        compute='_compute_payments', groups='account.group_account_invoice,account.group_account_readonly',
    )


    @api.model_create_multi
    def create(self, vals_list):
        """ A batch of another company takes the salary journal of its company. """
        for vals in vals_list:
            if vals.get('company_id') and 'journal_id' not in vals:
                company = self.env['res.company'].browse(vals['company_id'])
                vals['journal_id'] = _default_salary_journal(self.with_company(company))
                if not vals['journal_id']:
                    raise UserError(self.env._('%s has no miscellaneous journal for the salaries: create one in '
                                               'Accounting first.', company.name))
        return super().create(vals_list)

    @api.onchange('company_id')
    def _onchange_company_id_journal(self):
        if self.company_id and self.journal_id.company_id != self.company_id:
            self.journal_id = _default_salary_journal(self.with_company(self.company_id))
    @api.depends('slip_ids.payment_state', 'slip_ids.state', 'slip_ids.move_id')
    def _compute_payments(self):
        for run in self:
            run.has_payslips_to_pay = any(slip._can_register_payment() for slip in run.slip_ids)
            run.payment_count = len(run.sudo().slip_ids.payment_ids) if run.env.user.has_groups(
                'account.group_account_invoice,account.group_account_readonly') else 0

    def _generate_payslips(self, employees, skip_errors=False):
        # the payslips generated, from the wizard or the monthly batch, take the salary journal of the batch
        return super(HrPayslipRun, self.with_context(journal_id=self.journal_id.id))._generate_payslips(
            employees, skip_errors=skip_errors)

    def done_payslip_run(self):
        for run in self:
            slips = run.slip_ids.filtered(lambda slip: slip.state in ('draft', 'verify'))
            if not (run.consolidated_move and slips):
                super(HrPayslipRun, run).done_payslip_run()
                continue
            # let the payslips reach the done state without an entry of their own,
            # then post one entry for all of them
            super(HrPayslipRun, run.with_context(hr_payroll_consolidated_move=True)).done_payslip_run()
            slips._create_consolidated_move()
        return True

    def action_register_payment(self):
        self.ensure_one()
        return self.slip_ids.action_register_payment()

    def action_open_payments(self):
        self.ensure_one()
        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.slip_ids.payment_ids.ids)],
            'context': {'create': False},
        }
