from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain


class HrAnnouncement(models.Model):
    """ A notice to the employees of a company, of departments, of job positions, of tags, or to some employees:
    published, it reaches each of them, who read it and, when asked, acknowledge it. """
    _name = 'hr.announcement'
    _inherit = ['mail.thread', 'hr.audience.mixin']
    _description = 'Announcement'
    _order = 'pinned desc, date_start desc, id desc'

    name = fields.Char(string='Title', required=True, translate=True, tracking=True)
    body = fields.Html(translate=True, sanitize_style=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    pinned = fields.Boolean(string='Important', tracking=True,
                            help='Shown first and highlighted, in My HR and in the top bar.')
    requires_ack = fields.Boolean(string='Requires Acknowledgement', tracking=True,
                                  help='Each employee confirms they have read and understood it.')
    remind_after_days = fields.Integer(
        string='Remind After (Days)',
        help='Remind once the employees who have not acknowledged it after that many days; 0 for no reminder.')
    date_start = fields.Datetime(string='Show From', required=True, default=fields.Datetime.now, tracking=True,
                                 help='Published on that day: later, the announcement is scheduled until then.')
    date_end = fields.Date(string='Show Until', tracking=True, help='Expires after that day; empty to keep it.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
        ('expired', 'Expired'),
    ], required=True, default='draft', index=True, tracking=True, copy=False)
    date_published = fields.Datetime(string='Published On', readonly=True, copy=False)
    date_reminded = fields.Datetime(string='Reminded On', readonly=True, copy=False)
    recipient_ids = fields.One2many('hr.announcement.read', 'announcement_id', string='Recipients', copy=False)
    recipient_count = fields.Integer(compute='_compute_rates', string='Number of Recipients')
    read_count = fields.Integer(compute='_compute_rates', string='Read')
    ack_count = fields.Integer(compute='_compute_rates', string='Acknowledged')
    read_rate = fields.Float(compute='_compute_rates', string='Read (%)')
    ack_rate = fields.Float(compute='_compute_rates', string='Acknowledged (%)')
    my_state = fields.Selection([('unread', 'Unread'), ('read', 'Read'), ('acknowledged', 'Acknowledged')],
                                compute='_compute_my_state', search='_search_my_state', string='My Status')

    @api.depends('recipient_ids.read_date', 'recipient_ids.ack_date')
    def _compute_rates(self):
        for announcement in self:
            lines = announcement.sudo().recipient_ids
            count = len(lines)
            announcement.recipient_count = count
            announcement.read_count = len(lines.filtered('read_date'))
            announcement.ack_count = len(lines.filtered('ack_date'))
            announcement.read_rate = announcement.read_count / count * 100 if count else 0.0
            announcement.ack_rate = announcement.ack_count / count * 100 if count else 0.0

    def _my_lines(self):
        return self.env['hr.announcement.read'].sudo().search(
            [('announcement_id', 'in', self.ids), ('employee_id.user_id', '=', self.env.uid)])

    @api.depends_context('uid')
    def _compute_my_state(self):
        lines = {line.announcement_id: line for line in self._my_lines()}
        for announcement in self:
            line = lines.get(announcement)
            announcement.my_state = (line.ack_date and 'acknowledged') or (line.read_date and 'read') or \
                ('unread' if line else False)

    def _search_my_state(self, operator, value):
        if operator not in ('=', 'in'):
            raise UserError(_('Search My Status with = or in.'))
        values = [value] if operator == '=' else value
        states = {
            'unread': Domain('read_date', '=', False),
            'read': Domain('read_date', '!=', False) & Domain('ack_date', '=', False),
            'acknowledged': Domain('ack_date', '!=', False),
        }
        wanted = [states[state] for state in values if state in states]
        if not wanted:
            return [('id', '=', False)]
        lines = self.env['hr.announcement.read'].sudo().search(
            Domain('employee_id.user_id', '=', self.env.uid) & Domain.OR(wanted))
        return [('id', 'in', lines.announcement_id.ids)]

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for announcement in self:
            if announcement.date_end and announcement.date_end < announcement.date_start.date():
                raise ValidationError(_('The announcement %s ends after it starts.', announcement.name))

    @api.constrains('audience', 'department_ids', 'job_ids', 'category_ids', 'employee_ids')
    def _check_publisher(self):
        """ HR publishes to anyone; a department manager only to the departments they manage. """
        # constraints run as the super user: the rights of the user decide, not the sudo
        if self.env.user._is_superuser() or self.env.user.has_group('hr.group_hr_user'):
            return
        managed = self._managed_departments()
        for announcement in self:
            if announcement.audience != 'department' or not announcement.department_ids or \
                    announcement.department_ids - managed:
                raise ValidationError(_('As a department manager, address your announcements to the departments you '
                                        'manage: %s.', ', '.join(managed.mapped('name')) or _('none')))

    @api.model
    def _managed_departments(self):
        managed = self.env['hr.department'].sudo().search([('manager_id.user_id', '=', self.env.uid)])
        return self.env['hr.department'].sudo().search([('id', 'child_of', managed.ids)])

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def action_publish(self):
        """ Published now, or scheduled until the day it shows from. """
        for announcement in self:
            if announcement.state != 'draft':
                raise UserError(_('Only a draft is published: %s is not.', announcement.name))
            announcement._check_publisher()
            if not announcement._audience():
                raise UserError(_('The announcement %s reaches no employee.', announcement.name))
        now = fields.Datetime.now()
        self.filtered(lambda a: a.date_start > now).write({'state': 'scheduled'})
        self.filtered(lambda a: a.date_start <= now)._publish()
        return True

    def _publish(self):
        for announcement in self.sudo():
            employees = announcement._audience()
            announcement.write({'state': 'published', 'date_published': fields.Datetime.now(),
                                'recipient_ids': [(0, 0, {'employee_id': employee.id}) for employee in employees]})
            announcement._notify(employees, _('Announcement: %s', announcement.name))

    def _notify(self, employees, subject):
        """ The recipients get it in their inbox, or by email, as they prefer. """
        self.ensure_one()
        partners = employees.sudo().user_id.partner_id
        if partners:
            self.sudo().message_notify(partner_ids=partners.ids, subject=subject, body=self.body or self.name,
                                       subtype_xmlid='mail.mt_note', email_layout_xmlid='mail.mail_notification_light')

    def action_draft(self):
        """ Back to draft, before it is published. """
        if any(announcement.state != 'scheduled' for announcement in self):
            raise UserError(_('Only a scheduled announcement goes back to draft: a published one is archived.'))
        self.write({'state': 'draft'})
        return True

    def action_remind(self):
        """ Remind the recipients who have not acknowledged it yet. """
        for announcement in self:
            if announcement.state != 'published' or not announcement.requires_ack:
                raise UserError(_('Only a published announcement asking for an acknowledgement is reminded.'))
            pending = announcement.sudo().recipient_ids.filtered(lambda line: not line.ack_date).employee_id
            announcement._notify(pending, _('Reminder: %s', announcement.name))
            announcement.sudo().date_reminded = fields.Datetime.now()
            announcement.message_post(body=_('%s employees reminded.', len(pending)), subtype_xmlid='mail.mt_note')
        return True

    def action_open_recipients(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Recipients'),
            'res_model': 'hr.announcement.read',
            'view_mode': 'list,pivot',
            'domain': [('announcement_id', '=', self.id)],
            'context': dict(self.env.context),
        }

    @api.model
    def _cron_announcements(self):
        """ Publish what is due, expire what ended, remind once after the days asked for. """
        now = fields.Datetime.now()
        self.search([('state', '=', 'scheduled'), ('date_start', '<=', now)])._publish()
        self.search([('state', '=', 'published'), ('date_end', '<', fields.Date.context_today(self))]).write(
            {'state': 'expired'})
        for announcement in self.search([('state', '=', 'published'), ('requires_ack', '=', True),
                                         ('remind_after_days', '>', 0), ('date_reminded', '=', False)]):
            if announcement.date_published + timedelta(days=announcement.remind_after_days) <= now and \
                    announcement.recipient_ids.filtered(lambda line: not line.ack_date):
                announcement.action_remind()

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def web_read(self, specification):
        """ Opening the announcement marks it read for its recipient. """
        result = super().web_read(specification)
        if len(self) == 1 and 'body' in specification:
            self._mark_read()
        return result

    def _mark_read(self):
        self._my_lines().filtered(lambda line: not line.read_date).write({'read_date': fields.Datetime.now()})

    def action_acknowledge(self):
        lines = self._my_lines()
        if not lines:
            raise UserError(_('This announcement is not addressed to you.'))
        now = fields.Datetime.now()
        lines.filtered(lambda line: not line.read_date).write({'read_date': now})
        lines.filtered(lambda line: not line.ack_date).write({'ack_date': now})
        return True

    @api.model
    def systray_data(self):
        """ The announcements of the user waiting for them: unread, or to acknowledge. """
        mine = self.search([('state', '=', 'published')])
        lines = {line.announcement_id: line for line in mine._my_lines()}
        waiting = mine.filtered(lambda a: a in lines and (
            not lines[a].read_date or (a.requires_ack and not lines[a].ack_date)))
        return {
            'count': len(waiting),
            'items': [{
                'id': announcement.id, 'name': announcement.name, 'pinned': announcement.pinned,
                'requires_ack': announcement.requires_ack, 'read': bool(lines[announcement].read_date),
                'date': fields.Date.to_string(announcement.date_start.date()),
            } for announcement in waiting[:8]],
        }


class HrAnnouncementRead(models.Model):
    """ An employee an announcement reached: when they read it, when they acknowledged it. """
    _name = 'hr.announcement.read'
    _description = 'Announcement Recipient'
    _order = 'announcement_id, employee_id'

    announcement_id = fields.Many2one('hr.announcement', required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='cascade', index=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    company_id = fields.Many2one(related='announcement_id.company_id', store=True)
    read_date = fields.Datetime(string='Read On')
    ack_date = fields.Datetime(string='Acknowledged On')
    is_read = fields.Boolean(compute='_compute_is', store=True, aggregator='sum')
    is_acknowledged = fields.Boolean(compute='_compute_is', store=True, aggregator='sum')

    _announcement_employee_uniq = models.Constraint('UNIQUE(announcement_id, employee_id)',
                                                    'An announcement reaches an employee once.')

    @api.depends('read_date', 'ack_date')
    def _compute_is(self):
        for line in self:
            line.is_read = bool(line.read_date)
            line.is_acknowledged = bool(line.ack_date)
