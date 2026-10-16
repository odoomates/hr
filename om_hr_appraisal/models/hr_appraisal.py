from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

# open appraisals: one at a time per employee is planned
OPEN_STATES = ('new', 'self', 'review')
# what the employee, and the manager, change on an appraisal besides their own feedback
EMPLOYEE_WRITABLE = {'employee_feedback'}
MANAGER_WRITABLE = {'manager_feedback', 'rating_id', 'meeting_date', 'date_deadline', 'goal_ids'}


class HrAppraisal(models.Model):
    """ The review of an employee: the employee assesses themselves, then the manager reviews and rates them.

    Each side writes in a feedback the other side reads only when it is their turn: the manager reads the self
    assessment once it is submitted, the employee reads the review of the manager once the appraisal is done. The
    feedbacks are stored in fields only the super user reads; the fields the users see are computed from them
    with these rules, so that they hold through the API too.
    """
    _name = 'hr.appraisal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Appraisal'
    _order = 'date_deadline desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, index=True, tracking=True)
    manager_id = fields.Many2one(
        'hr.employee', string='Manager', index=True, tracking=True,
        compute='_compute_manager_id', store=True, readonly=False, precompute=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True, index=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    kind = fields.Selection([('regular', 'Appraisal'), ('probation', 'Probation Review')],
                            string='Kind', required=True, default='regular')
    cycle_id = fields.Many2one('hr.appraisal.cycle', string='Cycle', index=True, ondelete='set null')
    date_deadline = fields.Date(string='Deadline', required=True, tracking=True,
                                default=lambda self: fields.Date.context_today(self) + timedelta(days=30))
    date_done = fields.Date(string='Done On', readonly=True, copy=False)
    meeting_date = fields.Datetime(string='Meeting', tracking=True)
    template_id = fields.Many2one('hr.appraisal.template', string='Feedback Template')
    state = fields.Selection([
        ('new', 'To Start'),
        ('self', 'Self Assessment'),
        ('review', 'Manager Review'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], required=True, default='new', copy=False, index=True, tracking=True)
    rating_id = fields.Many2one('hr.appraisal.rating', string='Rating', tracking=True)
    goal_ids = fields.One2many('hr.appraisal.goal', 'appraisal_id', string='Goals')

    employee_feedback_html = fields.Html(groups='base.group_system', copy=False, prefetch=False)
    manager_feedback_html = fields.Html(groups='base.group_system', copy=False, prefetch=False)
    employee_feedback = fields.Html(string="Employee's Feedback", compute='_compute_feedback',
                                    inverse='_inverse_employee_feedback', sanitize=True)
    manager_feedback = fields.Html(string="Manager's Feedback", compute='_compute_feedback',
                                   inverse='_inverse_manager_feedback', sanitize=True)
    is_employee = fields.Boolean(compute='_compute_roles')
    is_manager = fields.Boolean(compute='_compute_roles')
    is_hr = fields.Boolean(compute='_compute_roles')
    can_edit_employee_feedback = fields.Boolean(compute='_compute_roles')
    can_edit_manager_feedback = fields.Boolean(compute='_compute_roles')
    employee_feedback_hidden = fields.Boolean(compute='_compute_roles')
    manager_feedback_hidden = fields.Boolean(compute='_compute_roles')

    @api.depends('employee_id', 'kind')
    def _compute_name(self):
        for appraisal in self:
            label = _('Probation Review of %s') if appraisal.kind == 'probation' else _('Appraisal of %s')
            appraisal.name = label % (appraisal.employee_id.name or '')

    @api.depends('employee_id')
    def _compute_manager_id(self):
        for appraisal in self:
            appraisal.manager_id = appraisal.employee_id.parent_id

    # ------------------------------------------------------------------
    # Who reads and writes what
    # ------------------------------------------------------------------

    def _roles(self):
        """ :return: the roles of the current user on the appraisal: employee, manager, hr """
        self.ensure_one()
        roles = set()
        if self.env.su or self.env.user.has_group('hr.group_hr_user'):
            roles.add('hr')
        if self.employee_id.user_id and self.employee_id.user_id == self.env.user:
            roles.add('employee')
        # the reviewer: the manager, else the HR responsible of the contract, who gets the review to-do
        reviewer = self._manager_user()
        if reviewer and reviewer == self.env.user:
            roles.add('manager')
        return roles

    def _can_read_feedback(self, side):
        roles = self._roles()
        if side == 'employee':
            return bool(roles & {'hr', 'employee'}) or ('manager' in roles and self.state in ('review', 'done'))
        return bool(roles & {'hr', 'manager'}) or ('employee' in roles and self.state == 'done')

    def _can_write_feedback(self, side):
        roles = self._roles()
        if side == 'employee':
            return bool(roles & {'hr', 'employee'}) and self.state in ('new', 'self')
        return bool(roles & {'hr', 'manager'}) and self.state in ('new', 'self', 'review')

    @api.depends('state', 'employee_id', 'manager_id')
    @api.depends_context('uid')
    def _compute_roles(self):
        for appraisal in self:
            roles = appraisal._roles()
            appraisal.is_employee = 'employee' in roles
            appraisal.is_manager = 'manager' in roles
            appraisal.is_hr = 'hr' in roles
            appraisal.can_edit_employee_feedback = appraisal._can_write_feedback('employee')
            appraisal.can_edit_manager_feedback = appraisal._can_write_feedback('manager')
            appraisal.employee_feedback_hidden = not appraisal._can_read_feedback('employee')
            appraisal.manager_feedback_hidden = not appraisal._can_read_feedback('manager')

    @api.depends('employee_feedback_html', 'manager_feedback_html', 'state', 'employee_id', 'manager_id')
    @api.depends_context('uid')
    def _compute_feedback(self):
        for appraisal in self:
            stored = appraisal.sudo()
            appraisal.employee_feedback = stored.employee_feedback_html \
                if appraisal._can_read_feedback('employee') else False
            appraisal.manager_feedback = stored.manager_feedback_html \
                if appraisal._can_read_feedback('manager') else False

    def _inverse_employee_feedback(self):
        for appraisal in self:
            if not appraisal._can_write_feedback('employee'):
                raise AccessError(_('The self assessment of %s cannot be changed now.', appraisal.name))
            appraisal.sudo().employee_feedback_html = appraisal.employee_feedback

    def _inverse_manager_feedback(self):
        for appraisal in self:
            if not appraisal._can_write_feedback('manager'):
                raise AccessError(_('The review of %s cannot be changed now.', appraisal.name))
            appraisal.sudo().manager_feedback_html = appraisal.manager_feedback

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        Template = self.env['hr.appraisal.template']
        for vals in vals_list:
            if not vals.get('template_id') and vals.get('employee_id'):
                vals['template_id'] = Template._get_for_employee(
                    self.env['hr.employee'].browse(vals['employee_id'])).id
        appraisals = super().create(vals_list)
        for appraisal in appraisals.sudo():
            template = appraisal.template_id
            if template and not appraisal.employee_feedback_html:
                appraisal.employee_feedback_html = template.employee_feedback
            if template and not appraisal.manager_feedback_html:
                appraisal.manager_feedback_html = template.manager_feedback
        return appraisals

    def write(self, vals):
        if not self.env.su and not self.env.user.has_group('hr.group_hr_user'):
            for appraisal in self:
                roles = appraisal._roles()
                allowed = set()
                if 'employee' in roles:
                    allowed |= EMPLOYEE_WRITABLE
                if 'manager' in roles and appraisal.state != 'done':
                    allowed |= MANAGER_WRITABLE
                if set(vals) - allowed:
                    raise AccessError(_('You cannot change %(fields)s of %(appraisal)s.',
                                        fields=', '.join(sorted(set(vals) - allowed)), appraisal=appraisal.name))
        return super().write(vals)

    def unlink(self):
        if any(appraisal.state not in ('new', 'cancel') for appraisal in self):
            raise UserError(_('Only an appraisal to start or cancelled can be deleted.'))
        return super().unlink()

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _check_roles(self, *allowed):
        for appraisal in self:
            if not appraisal._roles() & set(allowed):
                raise UserError(_('This step of %s is not yours to take.', appraisal.name))

    def _todo(self, user, summary):
        """ A to-do for the user whose turn it is, replacing the to-dos of the previous step. """
        self.ensure_one()
        self.sudo().activity_unlink(['mail.mail_activity_data_todo'])
        if user and user.active and not user.share:
            self.sudo().activity_schedule('mail.mail_activity_data_todo', date_deadline=self.date_deadline,
                                          summary=summary, user_id=user.id)

    def _manager_user(self):
        """ The user reviewing: the manager, else the HR responsible of the employee. """
        self.ensure_one()
        return self.manager_id.user_id or self.employee_id.sudo().version_id.hr_responsible_id

    def action_start(self):
        """ The employee assesses themselves; without a user, the manager reviews straight away. """
        self._check_roles('hr', 'manager')
        for appraisal in self:
            if appraisal.state != 'new':
                raise UserError(_('%s is already started.', appraisal.name))
            if appraisal.employee_id.user_id and appraisal.kind != 'probation':
                appraisal.sudo().state = 'self'
                appraisal._todo(appraisal.employee_id.user_id, _('Fill in your self assessment'))
            else:
                appraisal.sudo().state = 'review'
                appraisal._todo(appraisal._manager_user(), _('Review %s', appraisal.employee_id.name))
        return True

    def action_submit_self(self):
        self._check_roles('hr', 'employee')
        for appraisal in self:
            if appraisal.state != 'self':
                raise UserError(_('%s is not waiting for a self assessment.', appraisal.name))
            appraisal.sudo().state = 'review'
            appraisal._todo(appraisal._manager_user(), _('Review %s', appraisal.employee_id.name))
        return True

    def action_back_to_self(self):
        """ The manager hands the self assessment back to the employee, e.g. to complete it. """
        self._check_roles('hr', 'manager')
        for appraisal in self:
            if appraisal.state != 'review' or not appraisal.employee_id.user_id:
                raise UserError(_('%s cannot go back to the employee.', appraisal.name))
            appraisal.sudo().state = 'self'
            appraisal._todo(appraisal.employee_id.user_id, _('Complete your self assessment'))
        return True

    def action_done(self):
        self._check_roles('hr', 'manager')
        for appraisal in self:
            if appraisal.state != 'review':
                raise UserError(_('%s is not in review.', appraisal.name))
            if not appraisal.rating_id:
                raise UserError(_('Rate %s before closing the appraisal.', appraisal.employee_id.name))
            appraisal.sudo().write({'state': 'done', 'date_done': fields.Date.context_today(appraisal)})
            appraisal.sudo().activity_unlink(['mail.mail_activity_data_todo'])
            if appraisal.employee_id.user_id:
                appraisal.message_post(
                    body=_('Your appraisal is done: you can read the review of your manager.'),
                    partner_ids=appraisal.employee_id.user_id.partner_id.ids,
                    message_type='comment', subtype_xmlid='mail.mt_comment')
        return True

    def action_cancel(self):
        for appraisal in self:
            roles = appraisal._roles()
            if 'hr' not in roles and not ('manager' in roles and appraisal.state == 'new'):
                raise UserError(_('HR cancels a started appraisal.'))
            appraisal.sudo().state = 'cancel'
            appraisal.sudo().activity_unlink(['mail.mail_activity_data_todo'])
        return True

    def action_reset(self):
        self._check_roles('hr')
        self.filtered(lambda appraisal: appraisal.state == 'cancel').sudo().state = 'new'
        return True

    def action_new_contract_version(self):
        """ Record the raise or the promotion decided: a new version of the contract, from a date. """
        self.ensure_one()
        self._check_roles('hr')
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Contract Version'),
            'res_model': 'hr.appraisal.version',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_appraisal_id': self.id},
        }

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    @api.model
    def _cron_plan_appraisals(self):
        today = fields.Date.context_today(self)
        for company in self.env['res.company'].search([]):
            employees = self.env['hr.employee'].search([('company_id', '=', company.id)])
            if company.appraisal_probation:
                self._plan_probation_reviews(employees, today, company)
            if company.appraisal_auto:
                self._plan_regular_appraisals(employees, today, company)

    @api.model
    def _plan_probation_reviews(self, employees, today, company):
        horizon = today + timedelta(days=company.appraisal_probation_days)
        for employee in employees:
            trial_end = employee.sudo().version_id.trial_date_end
            if not trial_end or not today <= trial_end <= horizon:
                continue
            if self.search_count([('employee_id', '=', employee.id), ('kind', '=', 'probation'),
                                  ('date_deadline', '=', trial_end)]):
                continue
            appraisal = self.create({'employee_id': employee.id, 'kind': 'probation', 'date_deadline': trial_end})
            appraisal.action_start()

    @api.model
    def _plan_regular_appraisals(self, employees, today, company):
        horizon = today + timedelta(days=company.appraisal_lead_days)
        open_employees = set(self.search(
            [('employee_id', 'in', employees.ids), ('state', 'in', OPEN_STATES)]).employee_id.ids)
        for employee in employees:
            if employee.id in open_employees:
                continue
            due = employee._next_appraisal_date()
            if due and due <= horizon:
                appraisal = self.create({'employee_id': employee.id, 'date_deadline': max(due, today)})
                appraisal.action_start()

    @api.model
    def _next_date(self, employee):
        """ :return: when the next appraisal of the employee is due, by the settings of their company """
        company = employee.company_id
        last = self.search([('employee_id', '=', employee.id), ('state', '=', 'done')],
                           order='date_done desc', limit=1)
        if last and company.appraisal_interval_months:
            return last.date_done + relativedelta(months=company.appraisal_interval_months)
        start = employee.sudo().version_id.contract_date_start
        if not last and start and company.appraisal_first_months:
            return start + relativedelta(months=company.appraisal_first_months)
        return False
