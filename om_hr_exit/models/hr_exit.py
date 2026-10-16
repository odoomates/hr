from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

OPEN_STATES = ('draft', 'to_approve', 'approved')
TODO = 'mail.mail_activity_data_todo'


class HrExit(models.Model):
    """ An employee leaving the company: a resignation, or a contract HR ends. Approved along the approval flow of
        the exits, cleared during the notice period, then registered as the departure of the employee. """
    _name = 'hr.exit'
    _inherit = ['approval.mixin']
    _description = 'Employee Exit'
    _check_company_auto = True
    _order = 'date_notice desc, id desc'
    _mail_post_access = 'read'

    name = fields.Char(string='Reference', required=True, readonly=True, copy=False,
                       default=lambda self: self.env._('New'))
    employee_id = fields.Many2one(
        'hr.employee', required=True, index=True, tracking=True,
        default=lambda self: self.env.user.employee_id, check_company=True)
    company_id = fields.Many2one(
        'res.company', required=True, index=True,
        compute='_compute_company_id', store=True, readonly=False, precompute=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    job_id = fields.Many2one(related='employee_id.job_id', store=True)
    departure_reason_id = fields.Many2one(
        'hr.departure.reason', string='Reason', required=True, tracking=True, ondelete='restrict',
        default=lambda self: self.env.ref('hr.departure_resigned', raise_if_not_found=False))
    date_notice = fields.Date(string='Notice Given On', required=True, tracking=True,
                              default=fields.Date.context_today)
    notice_days = fields.Integer(
        string='Notice Period (Days)', compute='_compute_notice_days', store=True, readonly=False, precompute=True)
    last_working_day = fields.Date(
        compute='_compute_last_working_day', store=True, readonly=False,
        precompute=True, required=True, tracking=True)
    note = fields.Text(string='Details', help='Why the employee leaves, in his words or in those of HR.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('approved', 'Notice Period'),
        ('done', 'Left'),
        ('refused', 'Refused'),
        ('cancel', 'Cancelled'),
    ], required=True, default='draft', copy=False, index=True, tracking=True,
        help='Notice Period: approved, the employee is cleared until the last working day. Left: the departure of '
             'the employee is registered.')
    clearance_ids = fields.One2many('hr.exit.clearance', 'exit_id', copy=False)
    clearance_progress = fields.Float(compute='_compute_clearance', string='Cleared (%)')
    is_cleared = fields.Boolean(compute='_compute_clearance')
    departure_id = fields.Many2one('hr.employee.departure', readonly=True, copy=False)
    interview_date = fields.Date(groups='hr.group_hr_user')
    interview_note = fields.Html(string='Exit Interview', groups='hr.group_hr_user')
    would_rejoin = fields.Selection(
        [('yes', 'Yes'), ('maybe', 'Maybe'), ('no', 'No')], string='Would Come Back', groups='hr.group_hr_user')

    @api.depends('employee_id')
    def _compute_company_id(self):
        for exit_ in self:
            exit_.company_id = exit_.employee_id.company_id or exit_.company_id or self.env.company

    @api.depends('company_id')
    def _compute_notice_days(self):
        for exit_ in self:
            exit_.notice_days = (exit_.company_id or self.env.company).hr_exit_notice_days

    @api.depends('date_notice', 'notice_days')
    def _compute_last_working_day(self):
        for exit_ in self:
            if exit_.date_notice:
                exit_.last_working_day = exit_.date_notice + relativedelta(days=exit_.notice_days or 0)

    @api.depends('clearance_ids.state')
    def _compute_clearance(self):
        for exit_ in self:
            lines = exit_.clearance_ids
            closed = lines.filtered(lambda line: line.state != 'pending')
            exit_.clearance_progress = 100.0 * len(closed) / len(lines) if lines else 100.0
            exit_.is_cleared = len(closed) == len(lines)

    @api.constrains('date_notice', 'last_working_day')
    def _check_dates(self):
        for exit_ in self:
            if exit_.last_working_day < exit_.date_notice:
                raise ValidationError(self.env._('The last working day of %s comes after the notice.', exit_.name))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', self.env._('New')) == self.env._('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.exit') or self.env._('New')
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_submitted(self):
        if any(exit_.state not in ('draft', 'cancel') for exit_ in self):
            raise UserError(self.env._('Only a draft or a cancelled exit can be deleted.'))

    # ------------------------------------------------------------------
    # Approval
    # ------------------------------------------------------------------

    def action_submit(self):
        for exit_ in self:
            if exit_.state != 'draft':
                raise UserError(self.env._('Only a draft can be submitted: %s is not.', exit_.name))
            if self.search_count([('id', '!=', exit_.id), ('employee_id', '=', exit_.employee_id.id),
                                  ('state', 'in', ('to_approve', 'approved'))], limit=1):
                raise UserError(self.env._('%s already has an exit in progress.', exit_.employee_id.name))
        return self.action_approval_submit()

    def _approval_employee(self):
        self.ensure_one()
        return self.employee_id

    def _approval_check_requester(self):
        self.ensure_one()
        if self.employee_id.user_id != self.env.user and not self.env.user.has_group('hr.group_hr_user'):
            raise UserError(self.env._('Only %(employee)s or HR can change %(exit)s.',
                                       employee=self.employee_id.name, exit=self.name))

    def _on_approval_submitted(self, request):
        self.sudo().state = 'to_approve'

    def _on_approval_approved(self, request):
        result = super()._on_approval_approved(request)
        self.sudo().state = 'approved'
        self.sudo()._create_clearance()
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
        if any(exit_.state not in ('draft', 'to_approve') for exit_ in self):
            raise UserError(self.env._('An approved exit is cancelled by HR.'))
        result = super().action_approval_cancel()
        self.sudo().state = 'cancel'
        return result

    # ------------------------------------------------------------------
    # Clearance and departure
    # ------------------------------------------------------------------

    def _create_clearance(self):
        """ A clearance line per item of the checklist applying to the reason of the exit, with a to-do for the
            users clearing it. """
        for exit_ in self:
            items = self.env['hr.exit.checklist'].search([
                ('company_id', 'in', [False, exit_.company_id.id])]).filtered(
                lambda item: not item.departure_reason_ids or exit_.departure_reason_id in item.departure_reason_ids)
            lines = self.env['hr.exit.clearance'].create([{
                'exit_id': exit_.id,
                'checklist_id': item.id,
                'sequence': item.sequence,
                'name': item.name,
                'description': item.description,
                'responsible_user_ids': item._get_responsibles(exit_.employee_id).ids,
            } for item in items])
            for line in lines:
                for user in line.responsible_user_ids:
                    exit_.activity_schedule(TODO, date_deadline=exit_.last_working_day, user_id=user.id,
                                            summary=line._activity_summary(), note=line.description or '')

    def action_done(self):
        """ Register the departure of the employee: core HR ends the contract on the last working day, and archives
            the employee, and his user, the day after. """
        self._check_hr()
        for exit_ in self:
            if exit_.state != 'approved':
                raise UserError(self.env._('Only an approved exit is closed: %s is not.', exit_.name))
            if not exit_.is_cleared:
                raise UserError(self.env._('Clear every line of %s first, or mark the ones that do not apply as not '
                                           'needed.', exit_.name))
            departure = self.env['hr.employee.departure'].sudo().create({
                'employee_id': exit_.employee_id.id,
                'departure_reason_id': exit_.departure_reason_id.id,
                'departure_description': exit_.note,
                'dismissal_date': exit_.date_notice,
                'departure_date': exit_.last_working_day,
                'action_date': exit_.last_working_day + relativedelta(days=1),
            })
            exit_.write({'state': 'done', 'departure_id': departure.id})
            if departure.apply_immediately:
                departure.action_register()
        return True

    def action_cancel_approved(self):
        """ The employee stays after all: withdraw an approved exit, and its departure when not applied yet. """
        self._check_hr()
        for exit_ in self:
            if exit_.state not in ('approved', 'done'):
                raise UserError(self.env._('Only an approved or closed exit is cancelled this way: %s.', exit_.name))
            if exit_.departure_id:
                if exit_.departure_id.apply_date:
                    raise UserError(self.env._('%s has already left: register him as a new employee instead.',
                                               exit_.employee_id.name))
                exit_.employee_id.sudo().action_cancel_departure()
            exit_.clearance_ids.filtered(lambda line: line.state == 'pending').write({'state': 'not_needed'})
            exit_.activity_unlink([TODO], only_automated=True)
            exit_.write({'state': 'cancel', 'approval_state': 'cancel'})
        return True

    def _check_hr(self):
        if not self.env.user.has_group('hr.group_hr_user'):
            raise UserError(self.env._('Only HR closes or cancels an approved exit.'))


class HrExitClearance(models.Model):
    """ One item of the checklist an exit is cleared with. """
    _name = 'hr.exit.clearance'
    _description = 'Exit Clearance'
    _check_company_auto = True
    _order = 'exit_id, sequence, id'

    exit_id = fields.Many2one('hr.exit', required=True, ondelete='cascade', index=True, check_company=True)
    employee_id = fields.Many2one(related='exit_id.employee_id', store=True)
    company_id = fields.Many2one(related='exit_id.company_id', store=True)
    last_working_day = fields.Date(related='exit_id.last_working_day')
    checklist_id = fields.Many2one('hr.exit.checklist', string='Checklist Item', ondelete='set null',
                                   check_company=True)
    sequence = fields.Integer()
    name = fields.Char(required=True)
    description = fields.Text()
    responsible_user_ids = fields.Many2many('res.users', string='Cleared By')
    state = fields.Selection([('pending', 'To Clear'), ('done', 'Cleared'), ('not_needed', 'Not Needed')],
                             required=True, default='pending', index=True)
    user_id = fields.Many2one('res.users', string='Closed By', readonly=True)
    date = fields.Date(string='Closed On', readonly=True)
    note = fields.Char()

    def _activity_summary(self):
        self.ensure_one()
        return self.env._('Clearance: %s', self.name)

    def _close(self, state):
        for line in self:
            if line.exit_id.state != 'approved':
                raise UserError(self.env._('The exit %s is not in its notice period.', line.exit_id.name))
            if self.env.user not in line.responsible_user_ids and not self.env.user.has_group('hr.group_hr_user'):
                raise UserError(self.env._('%(item)s is cleared by %(users)s.', item=line.name,
                                           users=', '.join(line.responsible_user_ids.mapped('name'))))
            line.sudo().write({'state': state, 'user_id': self.env.user.id,
                               'date': fields.Date.context_today(self)})
            summary = line._activity_summary()
            line.exit_id.sudo().activity_ids.filtered(lambda activity: activity.summary == summary).action_feedback(
                feedback=dict(self._fields['state'].selection)[state])

    def action_clear(self):
        self._close('done')
        return True

    def action_not_needed(self):
        self._close('not_needed')
        return True

    def action_reopen(self):
        if not self.env.user.has_group('hr.group_hr_user'):
            raise UserError(self.env._('Only HR reopens a clearance line.'))
        self.filtered(lambda line: line.exit_id.state == 'approved').write(
            {'state': 'pending', 'user_id': False, 'date': False})
        return True
