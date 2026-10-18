from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from .hr_appraisal import OPEN_STATES


class HrOneOnOne(models.Model):
    """ A regular meeting of a manager with an employee. Both write the shared notes; the private notes of the
    manager are stored where only the super user reads them, and shown to the manager and to HR only. """
    _name = 'hr.one.on.one'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'One-on-One'
    _check_company_auto = True
    _order = 'date desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', required=True, index=True, tracking=True, check_company=True)
    manager_id = fields.Many2one(
        'hr.employee', index=True, tracking=True, check_company=True,
        compute='_compute_manager_id', store=True, readonly=False, precompute=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True, index=True)
    date = fields.Datetime(required=True, tracking=True, default=fields.Datetime.now)
    state = fields.Selection([
        ('planned', 'Planned'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], required=True, default='planned', copy=False, index=True, tracking=True)
    repeat_weeks = fields.Integer(
        string='Repeat Every', default=0,
        help='Weeks until the next one-on-one, planned when this one is done. 0 plans none.')
    appraisal_id = fields.Many2one(
        'hr.appraisal', index=True, ondelete='set null', check_company=True,
        compute='_compute_appraisal_id', store=True, readonly=False, precompute=True,
        help='The open appraisal of the employee, which the one-on-one prepares.')
    notes = fields.Html(string='Shared Notes', sanitize=True)
    manager_note_html = fields.Html(groups='base.group_system', copy=False, prefetch=False)
    manager_note = fields.Html(string='Private Notes', compute='_compute_manager_note',
                               inverse='_inverse_manager_note', sanitize=True,
                               help='Only the manager and HR read them, never the employee.')
    action_ids = fields.One2many('hr.one.on.one.action', 'one_on_one_id', string='Actions')
    is_manager = fields.Boolean(compute='_compute_is_manager')

    @api.depends('employee_id')
    def _compute_name(self):
        for meeting in self:
            meeting.name = self.env._('One-on-One with %s', meeting.employee_id.name or '')

    @api.depends('employee_id')
    def _compute_manager_id(self):
        for meeting in self:
            meeting.manager_id = meeting.employee_id.parent_id

    @api.depends('employee_id')
    def _compute_appraisal_id(self):
        for meeting in self:
            meeting.appraisal_id = self.env['hr.appraisal'].search([
                ('employee_id', '=', meeting.employee_id.id), ('state', 'in', OPEN_STATES)],
                order='date_deadline', limit=1) if meeting.employee_id else False

    def _can_read_manager_note(self):
        self.ensure_one()
        return self.env.su or self.env.user.has_group('hr.group_hr_user') \
            or (self.manager_id.user_id and self.manager_id.user_id == self.env.user)

    @api.depends('manager_note_html', 'manager_id')
    @api.depends_context('uid')
    def _compute_manager_note(self):
        for meeting in self:
            meeting.manager_note = meeting.sudo().manager_note_html if meeting._can_read_manager_note() else False

    def _inverse_manager_note(self):
        for meeting in self:
            if not meeting._can_read_manager_note():
                raise AccessError(self.env._('Only the manager writes the private notes of %s.', meeting.name))
            meeting.sudo().manager_note_html = meeting.manager_note

    @api.depends('manager_id')
    @api.depends_context('uid')
    def _compute_is_manager(self):
        for meeting in self:
            meeting.is_manager = meeting._can_read_manager_note()

    def write(self, vals):
        # the employee writes the shared notes only
        if not self.env.su and set(vals) - {'notes'}:
            for meeting in self:
                if not meeting._can_read_manager_note():
                    raise AccessError(self.env._('You write the shared notes of %s; your manager plans it.',
                                                 meeting.name))
        return super().write(vals)

    def action_done(self):
        for meeting in self:
            if not meeting._can_read_manager_note():
                raise UserError(self.env._('The manager closes %s.', meeting.name))
            if meeting.state != 'planned':
                raise UserError(self.env._('%s is not planned.', meeting.name))
            meeting.state = 'done'
            if meeting.repeat_weeks > 0:
                meeting.copy({
                    'date': meeting.date + timedelta(weeks=meeting.repeat_weeks),
                    'notes': False,
                })._compute_appraisal_id()
        return True

    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    def action_plan(self):
        self.write({'state': 'planned'})
        return True


class HrOneOnOneAction(models.Model):
    """ What the manager or the employee committed to in a one-on-one: a to-do for them, on the one-on-one. """
    _name = 'hr.one.on.one.action'
    _description = 'One-on-One Action'
    _order = 'done, date_deadline, id'

    one_on_one_id = fields.Many2one('hr.one.on.one', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one(related='one_on_one_id.company_id', store=True)
    name = fields.Char(string='Action', required=True)
    user_id = fields.Many2one('res.users', string='Who', domain=[('share', '=', False)])
    date_deadline = fields.Date(string='Due Date')
    done = fields.Boolean()
    activity_id = fields.Many2one('mail.activity', ondelete='set null', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        actions = super().create(vals_list)
        actions._schedule()
        return actions

    def write(self, vals):
        result = super().write(vals)
        if 'done' in vals:
            for action in self.filtered(lambda a: a.done and a.activity_id):
                action.activity_id.sudo().action_feedback(feedback=self.env._('Done'))
        if {'name', 'user_id', 'date_deadline'} & set(vals):
            self.filtered(lambda a: not a.done)._schedule()
        return result

    def unlink(self):
        self.activity_id.sudo().unlink()
        return super().unlink()

    def _schedule(self):
        """ The to-do of the action for the person who does it, replacing the one scheduled before. """
        for action in self:
            action.activity_id.sudo().unlink()
            if action.done or not action.user_id:
                continue
            action.activity_id = action.one_on_one_id.sudo().activity_schedule(
                'mail.mail_activity_data_todo', summary=action.name, user_id=action.user_id.id,
                date_deadline=action.date_deadline or fields.Date.context_today(action))
