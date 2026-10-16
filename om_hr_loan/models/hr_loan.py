from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

# states of a loan the employee still owes, or may still owe once approved
OPEN_STATES = ('to_approve', 'approved', 'running')


class HrLoan(models.Model):
    """ Money lent to an employee, approved along the approval flow of the loans, then repaid in installments. """
    _name = 'hr.loan'
    _inherit = ['approval.mixin']
    _description = 'Employee Loan'
    _order = 'date desc, id desc'
    _mail_post_access = 'read'

    name = fields.Char(string='Reference', required=True, readonly=True, copy=False,
                       default=lambda self: self.env._('New'))
    employee_id = fields.Many2one(
        'hr.employee', required=True, index=True, tracking=True,
        default=lambda self: self.env.user.employee_id)
    company_id = fields.Many2one(
        'res.company', required=True, index=True,
        compute='_compute_company_id', store=True, readonly=False, precompute=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    type_id = fields.Many2one(
        'hr.loan.type', required=True, tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    type_description = fields.Text(related='type_id.description')
    is_advance = fields.Boolean(related='type_id.is_advance')
    date = fields.Date(string='Asked On', required=True, default=fields.Date.context_today)
    amount = fields.Monetary(required=True, tracking=True)
    installment_count = fields.Integer(string='Installments', required=True, default=1, tracking=True)
    date_start = fields.Date(
        string='First Installment', required=True, tracking=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1) + relativedelta(months=1),
        help='The month of the first installment. The installments follow month after month.')
    reason = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('running', 'Repaying'),
        ('paid', 'Repaid'),
        ('refused', 'Refused'),
        ('cancel', 'Cancelled'),
    ], required=True, default='draft', copy=False, index=True, tracking=True,
        help='Approved: the loan waits to be paid out to the employee. Repaying: the installments are due.')
    date_disbursed = fields.Date(string='Paid Out On', copy=False, readonly=True)
    line_ids = fields.One2many('hr.loan.line', 'loan_id', string='Installment Lines', copy=False)
    installment_amount = fields.Monetary(compute='_compute_installment_amount', string='Installment')
    amount_paid = fields.Monetary(compute='_compute_amounts', string='Repaid', store=True)
    amount_residual = fields.Monetary(compute='_compute_amounts', string='Still Due', store=True)

    @api.depends('employee_id')
    def _compute_company_id(self):
        for loan in self:
            loan.company_id = loan.employee_id.company_id or loan.company_id or self.env.company

    @api.depends('amount', 'state', 'line_ids.amount', 'line_ids.state')
    def _compute_amounts(self):
        for loan in self:
            paid = sum(loan.line_ids.filtered(lambda installment: installment.state == 'paid').mapped('amount'))
            loan.amount_paid = paid
            loan.amount_residual = loan.amount - paid if loan.state not in ('draft', 'refused', 'cancel') else 0.0

    @api.depends('amount', 'installment_count', 'line_ids.amount')
    def _compute_installment_amount(self):
        for loan in self:
            loan.installment_amount = loan.line_ids[:1].amount or (
                loan.currency_id.round(loan.amount / loan.installment_count) if loan.installment_count > 0 else 0.0)

    @api.onchange('type_id')
    def _onchange_type_id(self):
        if self.type_id.is_advance:
            self.installment_count = 1

    @api.constrains('amount', 'installment_count')
    def _check_amounts(self):
        for loan in self:
            if loan.amount <= 0:
                raise ValidationError(self.env._('The amount of the loan %s must be positive.', loan.name))
            if loan.installment_count < 1:
                raise ValidationError(self.env._('The loan %s needs at least one installment.', loan.name))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', self.env._('New')) == self.env._('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.loan') or self.env._('New')
        return super().create(vals_list)

    def write(self, vals):
        schedule = {'amount', 'installment_count', 'date_start'}
        if schedule & set(vals) and any(loan.state != 'draft' for loan in self):
            raise UserError(self.env._('The amount and the installments of a loan only change while it is a draft.'))
        result = super().write(vals)
        if schedule & set(vals):
            self.filtered(lambda loan: loan.line_ids)._compute_installments()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_submitted(self):
        if any(loan.state not in ('draft', 'cancel') for loan in self):
            raise UserError(self.env._('Only a draft or a cancelled loan can be deleted.'))

    # ------------------------------------------------------------------
    # Installments
    # ------------------------------------------------------------------

    def _compute_installments(self):
        """ Spread the amount over the installments, one a month from the first installment. The last one takes
            what the rounding leaves, so that they add up to the amount. """
        for loan in self:
            if loan.state != 'draft':
                raise UserError(self.env._('The installments of %s are set once it is submitted.', loan.name))
            count = 1 if loan.is_advance else loan.installment_count
            installment = loan.currency_id.round(loan.amount / count)
            first = loan.date_start.replace(day=1)
            values = [{
                'sequence': index + 1,
                'date': first + relativedelta(months=index),
                'amount': installment if index < count - 1 else loan.amount - installment * (count - 1),
            } for index in range(count)]
            loan.line_ids = [fields.Command.clear()] + [fields.Command.create(vals) for vals in values]

    def action_compute_installments(self):
        self._compute_installments()
        return True

    def _check_limits(self):
        """ Raise when the loan goes beyond the limits of its type. """
        self.ensure_one()
        loan_type = self.type_id
        count = len(self.line_ids)
        if loan_type.max_amount and self.amount > loan_type.max_amount:
            raise UserError(self.env._('A %(type)s is %(max)s at most.', type=loan_type.name,
                                       max=self.currency_id.format(loan_type.max_amount)))
        if loan_type.max_installments and count > loan_type.max_installments:
            raise UserError(self.env._('A %(type)s is repaid in %(max)s installments at most.', type=loan_type.name,
                                       max=loan_type.max_installments))
        employee = self.employee_id.sudo()
        if loan_type.min_service_months:
            start = employee.first_contract_date
            if not start or start + relativedelta(months=loan_type.min_service_months) > self.date:
                raise UserError(self.env._('%(employee)s needs %(months)s months of service for a %(type)s.',
                                           employee=employee.name, months=loan_type.min_service_months,
                                           type=loan_type.name))
        if loan_type.max_wage_percent:
            wage = employee.version_id.wage
            limit = wage * loan_type.max_wage_percent / 100
            if max(self.line_ids.mapped('amount')) > limit:
                raise UserError(self.env._('An installment of a %(type)s is %(percent)s%% of the wage at most, '
                                           '%(limit)s: spread the loan over more installments.', type=loan_type.name,
                                           percent=loan_type.max_wage_percent, limit=self.currency_id.format(limit)))
        if loan_type.single_running and self.search_count([
                ('id', '!=', self.id), ('employee_id', '=', self.employee_id.id),
                ('type_id', '=', loan_type.id), ('state', 'in', OPEN_STATES)], limit=1):
            raise UserError(self.env._('%(employee)s already has a %(type)s to repay or to approve.',
                                       employee=employee.name, type=loan_type.name))

    # ------------------------------------------------------------------
    # Approval
    # ------------------------------------------------------------------

    def action_submit(self):
        for loan in self:
            if loan.state != 'draft':
                raise UserError(self.env._('Only a draft can be submitted: %s is not.', loan.name))
            if not loan.line_ids:
                loan._compute_installments()
            loan._check_limits()
        return self.action_approval_submit()

    def _approval_employee(self):
        self.ensure_one()
        return self.employee_id

    def _approval_check_requester(self):
        self.ensure_one()
        if self.employee_id.user_id != self.env.user and not self.env.user.has_group('hr.group_hr_user'):
            raise UserError(self.env._('Only %(employee)s or HR can change %(loan)s.',
                                       employee=self.employee_id.name, loan=self.name))

    def _on_approval_submitted(self, request):
        self.sudo().state = 'to_approve'

    def _on_approval_approved(self, request):
        result = super()._on_approval_approved(request)
        self.sudo().state = 'approved'
        return result

    def _on_approval_refused(self, request):
        result = super()._on_approval_refused(request)
        self.sudo().state = 'refused'
        return result

    def _on_approval_cancelled(self, request):
        result = super()._on_approval_cancelled(request)
        self.sudo().state = 'cancel'
        return result

    def _on_approval_reset(self):
        self.sudo().state = 'draft'

    def action_approval_cancel(self):
        if any(loan.state not in ('draft', 'to_approve') for loan in self):
            raise UserError(self.env._('An approved loan is cancelled by HR, before it is paid out.'))
        result = super().action_approval_cancel()
        self.sudo().state = 'cancel'
        return result

    # ------------------------------------------------------------------
    # Repayment
    # ------------------------------------------------------------------

    def action_disburse(self):
        """ The loan is paid out to the employee: its installments become due. """
        self._check_hr()
        for loan in self:
            if loan.state != 'approved':
                raise UserError(self.env._('Only an approved loan is paid out: %s is not.', loan.name))
            loan.write({'state': 'running', 'date_disbursed': fields.Date.context_today(self)})
        return True

    def action_cancel_approved(self):
        """ Withdraw an approved loan not paid out yet. """
        self._check_hr()
        for loan in self:
            if loan.state != 'approved':
                raise UserError(self.env._('Only an approved loan not paid out yet is cancelled this way: %s.',
                                           loan.name))
            loan.write({'state': 'cancel', 'approval_state': 'cancel'})
        return True

    def action_settle(self):
        """ The employee repays everything still due at once, e.g. in cash or when leaving. """
        self._check_hr()
        for loan in self:
            if loan.state != 'running':
                raise UserError(self.env._('Only a loan being repaid is settled: %s is not.', loan.name))
            loan.line_ids.filtered(lambda installment: installment.state == 'to_pay')._mark_paid(self.env._('Settled '
                                                                                                            'at once'))
        return True

    def _check_hr(self):
        if not self.env.user.has_group('hr.group_hr_user'):
            raise UserError(self.env._('Only HR pays out, cancels or settles a loan.'))

    def _check_repaid(self):
        for loan in self.filtered(lambda loan: loan.state == 'running'):
            if loan.line_ids and all(line.state == 'paid' for line in loan.line_ids):
                loan.state = 'paid'
                loan.message_post(body=self.env._('Repaid.'), subtype_xmlid='mail.mt_note')


class HrLoanLine(models.Model):
    """ One monthly installment of a loan. """
    _name = 'hr.loan.line'
    _description = 'Loan Installment'
    _order = 'loan_id, date, id'

    loan_id = fields.Many2one('hr.loan', required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one(related='loan_id.employee_id', store=True)
    company_id = fields.Many2one(related='loan_id.company_id', store=True)
    currency_id = fields.Many2one(related='loan_id.currency_id')
    loan_state = fields.Selection(related='loan_id.state', string='Loan Status')
    sequence = fields.Integer()
    date = fields.Date(string='Month', required=True)
    amount = fields.Monetary(required=True)
    state = fields.Selection([('to_pay', 'To Repay'), ('paid', 'Repaid')], required=True, default='to_pay',
                             index=True)
    date_paid = fields.Date(string='Repaid On')
    note = fields.Char()

    def _mark_paid(self, note=False, date=False):
        self.write({'state': 'paid', 'date_paid': date or fields.Date.context_today(self), 'note': note})
        self.loan_id._check_repaid()

    def action_mark_paid(self):
        self.loan_id._check_hr()
        if any(line.loan_id.state != 'running' or line.state != 'to_pay' for line in self):
            raise UserError(self.env._('Only an installment due on a loan being repaid is marked as repaid.'))
        self._mark_paid(self.env._('Repaid outside the payroll'))
        return True

    def action_postpone(self):
        """ Move the installment, and the ones after it, one month later. """
        self.loan_id._check_hr()
        for line in self:
            if line.state != 'to_pay' or line.loan_id.state not in ('approved', 'running'):
                raise UserError(self.env._('Only an installment still due is postponed.'))
            later = line.loan_id.line_ids.filtered(
                lambda installment: installment.state == 'to_pay' and installment.date >= line.date)
            for installment in later.sorted('date', reverse=True):
                installment.date += relativedelta(months=1)
            line.loan_id.message_post(body=self.env._('Installment of %(month)s postponed by one month.',
                                                      month=(line.date - relativedelta(months=1)).strftime('%B %Y')),
                                      subtype_xmlid='mail.mt_note')
        return True
