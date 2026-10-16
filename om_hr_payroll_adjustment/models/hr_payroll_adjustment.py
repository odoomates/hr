from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class HrPayrollAdjustment(models.Model):
    """ An addition to or a deduction from the pay of an employee, e.g. a bonus or a fine: once, for a number of
    months, or every month until a total, of a fixed amount or of a percentage of the wage or of the gross. The
    payslips take its monthly lines as they fall due. """
    _name = 'hr.payroll.adjustment'
    _inherit = ['approval.mixin']
    _description = 'Payroll Adjustment'
    _order = 'date_start desc, id desc'
    _mail_post_access = 'read'

    name = fields.Char(string='Reference', required=True, readonly=True, copy=False, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, index=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        compute='_compute_company_id', store=True, readonly=False, precompute=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    type_id = fields.Many2one(
        'hr.payroll.adjustment.type', string='Type', required=True, tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    kind = fields.Selection(related='type_id.kind', store=True)
    description = fields.Char(help='Shown to the employee, e.g. "Q3 sales commission".')
    note = fields.Text(string='Internal Note')
    recurrence = fields.Selection([
        ('once', 'Once'),
        ('months', 'Monthly, for a number of months'),
        ('total', 'Monthly, until a total'),
    ], required=True, default='once', tracking=True)
    amount_type = fields.Selection([('fixed', 'Fixed Amount'), ('percent', 'Percentage')], string='Amount Type',
                                   required=True, default='fixed', tracking=True)
    amount = fields.Monetary(string='Amount per Month', tracking=True,
                             help='The amount paid or deducted each month.')
    percent = fields.Float(string='Percentage', digits=(16, 2), tracking=True)
    percent_base = fields.Selection([('wage', 'of the Wage'), ('gross', 'of the Gross')], string='Base',
                                    default='wage', tracking=True,
                                    help='The wage of the contract, or the gross of the payslip: deductions only.')
    month_count = fields.Integer(string='Months', default=1, tracking=True)
    total_amount = fields.Monetary(string='Total', tracking=True,
                                   help='Paid or deducted month after month until this total is reached.')
    date_start = fields.Date(
        string='First Month', required=True, tracking=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
        help='The month of the first payslip taking it.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('refused', 'Refused'),
        ('cancel', 'Cancelled'),
    ], required=True, default='draft', copy=False, index=True, tracking=True)
    line_ids = fields.One2many('hr.payroll.adjustment.line', 'adjustment_id', string='Monthly Lines', copy=False)
    amount_done = fields.Monetary(compute='_compute_amounts', string='Paid', store=True,
                                  help='Paid or deducted so far, by the confirmed payslips or by hand.')
    amount_residual = fields.Monetary(compute='_compute_amounts', string='Still Due', store=True)

    @api.depends('employee_id')
    def _compute_company_id(self):
        for adjustment in self:
            adjustment.company_id = adjustment.employee_id.company_id or adjustment.company_id or self.env.company

    @api.depends('state', 'recurrence', 'amount_type', 'total_amount', 'line_ids.amount', 'line_ids.state')
    def _compute_amounts(self):
        for adjustment in self:
            done = sum(adjustment.line_ids.filtered(lambda line: line.state == 'paid').mapped('amount'))
            adjustment.amount_done = done
            residual = 0.0
            if adjustment.state in ('to_approve', 'running'):
                if adjustment.recurrence == 'total':
                    residual = max(adjustment.total_amount - done, 0.0)
                elif adjustment.amount_type == 'fixed':
                    residual = sum(adjustment.line_ids.filtered(lambda line: line.state == 'to_pay').mapped('amount'))
            adjustment.amount_residual = residual

    @api.depends('name', 'type_id')
    def _compute_display_name(self):
        for adjustment in self:
            adjustment.display_name = '%s - %s' % (adjustment.name, adjustment.type_id.name) \
                if adjustment.type_id else adjustment.name

    @api.onchange('type_id')
    def _onchange_type_id(self):
        if self.type_id.kind == 'addition':
            self.percent_base = 'wage'

    @api.onchange('recurrence')
    def _onchange_recurrence(self):
        if self.recurrence == 'once':
            self.month_count = 1

    @api.constrains('amount_type', 'amount', 'percent', 'percent_base', 'recurrence', 'month_count', 'total_amount',
                    'type_id')
    def _check_amounts(self):
        for adjustment in self:
            if adjustment.amount_type == 'fixed' and adjustment.amount <= 0:
                raise ValidationError(_('The amount of %s must be positive.', adjustment.display_name))
            if adjustment.amount_type == 'percent':
                if not 0 < adjustment.percent <= 100:
                    raise ValidationError(_('The percentage of %s is between 0 and 100.', adjustment.display_name))
                if adjustment.percent_base == 'gross' and adjustment.kind != 'deduction':
                    raise ValidationError(_('Only a deduction is a percentage of the gross: an addition is part of '
                                            'the gross itself. Take a percentage of the wage for %s.',
                                            adjustment.display_name))
            if adjustment.recurrence == 'months' and adjustment.month_count < 1:
                raise ValidationError(_('%s runs for one month at least.', adjustment.display_name))
            if adjustment.recurrence == 'total' and adjustment.total_amount <= 0:
                raise ValidationError(_('The total of %s must be positive.', adjustment.display_name))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.payroll.adjustment') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        schedule = {'type_id', 'employee_id', 'recurrence', 'amount_type', 'amount', 'percent', 'percent_base',
                    'month_count', 'total_amount', 'date_start'}
        if schedule & set(vals) and any(adjustment.state != 'draft' for adjustment in self):
            raise UserError(_('An adjustment only changes while it is a draft: stop it and add a new one.'))
        return super().write(vals)

    def unlink(self):
        if any(adjustment.state not in ('draft', 'cancel') for adjustment in self):
            raise UserError(_('Only a draft or a cancelled adjustment can be deleted.'))
        return super().unlink()

    # ------------------------------------------------------------------
    # Monthly lines
    # ------------------------------------------------------------------

    def _month_count(self):
        """ :return: the number of monthly lines set in advance; an adjustment of a percentage until a total gets
            its lines month after month, its amounts being known only then """
        self.ensure_one()
        if self.recurrence == 'once':
            return 1
        if self.recurrence == 'months':
            return self.month_count
        if self.amount_type == 'percent':
            return 0
        return -(-self.currency_id.round(self.total_amount) // self.currency_id.round(self.amount))

    def _compute_lines(self):
        """ One line a month from the first month. A fixed amount is set now, the last month of a total taking what
            is left; a percentage is set by the payslip taking the line. """
        for adjustment in self:
            first = adjustment.date_start.replace(day=1)
            count = int(adjustment._month_count())
            values = []
            for index in range(count):
                amount = adjustment.amount if adjustment.amount_type == 'fixed' else 0.0
                if adjustment.recurrence == 'total' and index == count - 1:
                    amount = adjustment.total_amount - adjustment.amount * (count - 1)
                values.append({'date': first + relativedelta(months=index), 'amount': amount})
            adjustment.line_ids = [fields.Command.clear()] + [fields.Command.create(vals) for vals in values]

    # ------------------------------------------------------------------
    # Approval
    # ------------------------------------------------------------------

    def action_confirm(self):
        """ The adjustment runs, once approved when its type asks for it. """
        self._check_payroll()
        for adjustment in self:
            if adjustment.state != 'draft':
                raise UserError(_('Only a draft is confirmed: %s is not.', adjustment.display_name))
            adjustment._compute_lines()
        to_approve = self.filtered('type_id.require_approval')
        (self - to_approve).sudo().write({'state': 'running', 'approval_state': 'approved'})
        if to_approve:
            to_approve.action_approval_submit()
        return True

    def _approval_employee(self):
        self.ensure_one()
        return self.employee_id

    def _approval_check_requester(self):
        self._check_payroll()

    def _on_approval_submitted(self, request):
        self.sudo().state = 'to_approve'

    def _on_approval_approved(self, request):
        super()._on_approval_approved(request)
        self.sudo().state = 'running'

    def _on_approval_refused(self, request):
        super()._on_approval_refused(request)
        self.sudo().state = 'refused'

    def _on_approval_cancelled(self, request):
        super()._on_approval_cancelled(request)
        self.sudo().state = 'cancel'

    def _on_approval_reset(self):
        self.sudo().state = 'draft'
        self.line_ids.sudo().unlink()

    def action_approval_cancel(self):
        if any(adjustment.state not in ('draft', 'to_approve') for adjustment in self):
            raise UserError(_('A running adjustment is stopped, not cancelled.'))
        result = super().action_approval_cancel()
        self.sudo().state = 'cancel'
        return result

    # ------------------------------------------------------------------
    # Running
    # ------------------------------------------------------------------

    def action_stop(self):
        """ Nothing more is paid or deducted: the lines still due go. """
        self._check_payroll()
        for adjustment in self:
            if adjustment.state != 'running':
                raise UserError(_('Only a running adjustment is stopped: %s is not.', adjustment.display_name))
            adjustment.line_ids.filtered(lambda line: line.state == 'to_pay').unlink()
            adjustment.state = 'done' if adjustment.line_ids else 'cancel'
            adjustment.message_post(body=_('Stopped.'), subtype_xmlid='mail.mt_note')
        return True

    def _check_payroll(self):
        if not self.env.user.has_group('om_hr_payroll.group_hr_payroll_user'):
            raise UserError(_('Only the payroll officers manage the payroll adjustments.'))

    def _check_done(self):
        """ Done once every line is paid, and the total reached for an adjustment until a total. """
        for adjustment in self.filtered(lambda adjustment: adjustment.state == 'running'):
            lines = adjustment.line_ids
            if adjustment.recurrence == 'total':
                finished = adjustment.currency_id.compare_amounts(
                    sum(lines.filtered(lambda line: line.state == 'paid').mapped('amount')),
                    adjustment.total_amount) >= 0
            else:
                finished = lines and all(line.state == 'paid' for line in lines)
            if finished:
                lines.filtered(lambda line: line.state == 'to_pay').unlink()
                adjustment.state = 'done'


class HrPayrollAdjustmentLine(models.Model):
    """ What one month of an adjustment pays or deducts. """
    _name = 'hr.payroll.adjustment.line'
    _description = 'Payroll Adjustment Line'
    _order = 'adjustment_id, date, id'

    adjustment_id = fields.Many2one('hr.payroll.adjustment', required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one(related='adjustment_id.employee_id', store=True)
    company_id = fields.Many2one(related='adjustment_id.company_id', store=True)
    currency_id = fields.Many2one(related='adjustment_id.currency_id')
    type_id = fields.Many2one(related='adjustment_id.type_id', store=True)
    adjustment_state = fields.Selection(related='adjustment_id.state', string='Adjustment Status')
    date = fields.Date(string='Month', required=True)
    amount = fields.Monetary(help='Positive: the type of the adjustment says whether it is paid or deducted. A '
                                  'percentage is set by the payslip taking the line.')
    state = fields.Selection([('to_pay', 'Due'), ('paid', 'Done')], required=True, default='to_pay', index=True)
    payslip_id = fields.Many2one('hr.payslip', string='Payslip', ondelete='set null', index=True, copy=False)
    date_paid = fields.Date(string='Done On')
    note = fields.Char()

    def _mark_paid(self, note=False, date=False):
        self.write({'state': 'paid', 'date_paid': date or fields.Date.context_today(self), 'note': note})
        self.adjustment_id._check_done()

    def action_postpone(self):
        """ Move the line, and the ones after it, one month later. """
        self.adjustment_id._check_payroll()
        for line in self:
            if line.state != 'to_pay' or line.adjustment_id.state != 'running':
                raise UserError(_('Only a line still due on a running adjustment is postponed.'))
            if line.payslip_id and line.payslip_id.state not in ('draft', 'verify', 'cancel'):
                raise UserError(_('The payslip %s takes the line already.', line.payslip_id.display_name))
            later = line.adjustment_id.line_ids.filtered(lambda l: l.state == 'to_pay' and l.date >= line.date)
            later.payslip_id = False
            for other in later.sorted('date', reverse=True):
                other.date += relativedelta(months=1)
            line.adjustment_id.message_post(
                body=_('The month of %(month)s postponed by one month.',
                       month=(line.date - relativedelta(months=1)).strftime('%B %Y')),
                subtype_xmlid='mail.mt_note')
        return True

    def action_mark_paid(self):
        """ Paid or deducted outside the payroll. """
        self.adjustment_id._check_payroll()
        if any(line.state != 'to_pay' or line.adjustment_id.state != 'running' for line in self):
            raise UserError(_('Only a line still due on a running adjustment is marked as done.'))
        if any(line.adjustment_id.amount_type == 'percent' and not line.amount for line in self):
            raise UserError(_('Set the amount of a percentage before marking it as done.'))
        self._mark_paid(_('Done outside the payroll'))
        return True
