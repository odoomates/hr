from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.exceptions import UserError

from .hr_preboarding_step import BANK_FIELDS, DETAIL_FIELDS


class HrPreboarding(models.Model):
    """ What a new hire does before their first day: the steps of their company, done on the website, the details
    they give reviewed by HR before they are written on the employee. It closes on the first day. """
    _name = 'hr.preboarding'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Pre-boarding'
    _check_company_auto = True
    _order = 'date_start, id'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True, readonly=True,
                                  check_company=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True, index=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    user_id = fields.Many2one(related='employee_id.user_id')
    date_start = fields.Date(string='First Day', required=True, tracking=True)
    buddy_id = fields.Many2one('hr.employee', tracking=True, check_company=True,
                               help='The colleague who welcomes the new hire and answers their questions.')
    welcome = fields.Html(string='First Day Information', sanitize_style=True,
                          help='Shown to the new hire: when and where to come, whom to ask for.')
    state = fields.Selection([
        ('running', 'In Progress'),
        ('done', 'Completed'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], required=True, default='running', tracking=True, index=True, readonly=True)
    line_ids = fields.One2many('hr.preboarding.line', 'preboarding_id', string='Steps')
    progress = fields.Integer(compute='_compute_progress', string='Done (%)')
    to_review_count = fields.Integer(compute='_compute_progress', string='To Review')
    date_done = fields.Datetime(string='Completed On', readonly=True)

    @api.depends('line_ids.state')
    def _compute_progress(self):
        for preboarding in self:
            lines = preboarding.line_ids
            preboarding.progress = round(len(lines.filtered(lambda line: line.state == 'done')) / len(lines) * 100) \
                if lines else 100
            preboarding.to_review_count = len(lines.filtered(lambda line: line.state == 'submitted'))

    @api.depends('employee_id')
    def _compute_display_name(self):
        for preboarding in self:
            preboarding.display_name = self.env._('Pre-boarding of %s', preboarding.employee_id.name)

    # ------------------------------------------------------------------
    # Starting
    # ------------------------------------------------------------------

    @api.model
    def _start(self, employee, date_start=None):
        """ :return: the pre-boarding of `employee`, its steps those of the company reaching them """
        employee.ensure_one()
        date_start = date_start or employee.sudo().contract_date_start
        if not date_start:
            raise UserError(self.env._('Set the contract start date of %s first.', employee.name))
        if self.search_count([('employee_id', '=', employee.id), ('state', '=', 'running')]):
            raise UserError(self.env._('%s already has a pre-boarding in progress.', employee.name))
        company = employee.company_id
        steps = self.env['hr.preboarding.step'].search(
            [('company_id', '=', company.id)]).filtered(lambda step: step._in_audience(employee))
        preboarding = self.create({
            'employee_id': employee.id,
            'date_start': date_start,
            'buddy_id': employee.parent_id.id,
            'welcome': company.preboarding_welcome,
            'line_ids': [(0, 0, step._line_values()) for step in steps],
        })
        preboarding.line_ids._on_started()
        if not employee.user_id:
            employee.action_grant_portal()
        if company.preboarding_plan_id:
            self.env['mail.activity.schedule'].create({
                'res_model': 'hr.employee', 'res_ids': str(employee.ids),
                'plan_id': company.preboarding_plan_id.id, 'plan_date': date_start,
            }).action_schedule_plan()
        preboarding._notify_welcome()
        return preboarding

    def _get_url(self):
        self.ensure_one()
        return '%s/my/welcome' % self.get_base_url()

    def _notify_welcome(self):
        self.ensure_one()
        partner = self.employee_id.user_id.partner_id or self.employee_id.work_contact_id
        body = self.env['ir.qweb']._render('om_hr_preboarding.mail_preboarding_welcome', {
            'preboarding': self, 'url': self._get_url()})
        self.sudo().message_notify(partner_ids=partner.ids, subject=self.env._('Welcome to %s', self.company_id.name),
                                   body=body, email_layout_xmlid='mail.mail_notification_light')

    # ------------------------------------------------------------------
    # Following up
    # ------------------------------------------------------------------

    def _check_done(self):
        for preboarding in self.filtered(lambda p: p.state == 'running'):
            if all(line.state == 'done' for line in preboarding.line_ids):
                preboarding.sudo().write({'state': 'done', 'date_done': fields.Datetime.now()})
                preboarding.sudo().message_post(
                    body=self.env._('%s completed the pre-boarding.', preboarding.employee_id.name),
                    subtype_xmlid='mail.mt_note', partner_ids=preboarding.create_uid.partner_id.ids)

    def _refresh(self):
        """ Mark done the steps that other records complete, e.g. a document uploaded (see the bridges). """
        self.line_ids.filtered(lambda line: line.state != 'done')._refresh()
        self._check_done()

    @api.model
    def _cron_follow_up(self):
        """ Refresh the steps; close the pre-boardings on the first day. """
        running = self.search([('state', '=', 'running')])
        running._refresh()
        today = fields.Date.context_today(self)
        running.filtered(lambda p: p.state == 'running' and p.date_start <= today).sudo().state = 'closed'

    def _open(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }

    def action_cancel(self):
        self.filtered(lambda p: p.state == 'running').sudo().state = 'cancelled'
        return True

    def action_send_welcome(self):
        for preboarding in self:
            preboarding._notify_welcome()
        return True


class HrPreboardingLine(models.Model):
    """ A step of a pre-boarding, and what the new hire answered. """
    _name = 'hr.preboarding.line'
    _description = 'Pre-boarding Step of a New Hire'
    _order = 'sequence, id'

    preboarding_id = fields.Many2one('hr.preboarding', required=True, ondelete='cascade', index=True)
    preboarding_state = fields.Selection(related='preboarding_id.state', string='Pre-boarding Status')
    employee_id = fields.Many2one(related='preboarding_id.employee_id', store=True, index=True)
    company_id = fields.Many2one(related='preboarding_id.company_id', store=True, index=True)
    step_id = fields.Many2one('hr.preboarding.step', ondelete='set null')
    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    kind = fields.Selection(selection='_selection_kind', required=True)
    description = fields.Html(sanitize_style=True)
    state = fields.Selection([
        ('todo', 'To Do'),
        ('submitted', 'To Review'),
        ('returned', 'Sent Back'),
        ('done', 'Done'),
    ], required=True, default='todo', readonly=True)
    data = fields.Json(string='Answer', readonly=True)
    review_html = fields.Html(compute='_compute_review_html', string='Review', sanitize=False)
    review_note = fields.Text(readonly=True)
    date_done = fields.Datetime(string='Done On', readonly=True)
    needs_review = fields.Boolean(compute='_compute_needs_review')

    @api.model
    def _selection_kind(self):
        return self.env['hr.preboarding.step']._fields['kind']._description_selection(self.env)

    @api.depends('kind')
    def _compute_needs_review(self):
        kinds = self.env['hr.preboarding.step']._review_kinds()
        for line in self:
            line.needs_review = line.kind in kinds

    def _fields_of_kind(self):
        """ :return: the fields the new hire fills on the step, of hr.employee, or of res.partner.bank """
        self.ensure_one()
        if self.kind == 'bank':
            return self.env['res.partner.bank'], BANK_FIELDS
        return self.env['hr.employee'], DETAIL_FIELDS.get(self.kind, [])

    def _current_values(self):
        """ :return: the values the employee has now, as the form shows them """
        self.ensure_one()
        model, names = self._fields_of_kind()
        if model._name != 'hr.employee':
            return {}
        employee = self.employee_id.sudo()
        return {name: employee[name].id if model._fields[name].type == 'many2one' else employee[name]
                for name in names}

    @api.depends('data', 'kind')
    def _compute_review_html(self):
        for line in self:
            if not line.data or not line.needs_review:
                line.review_html = False
                continue
            model, names = line._fields_of_kind()
            current = line._current_values()
            rows = []
            for name in names:
                field = model._fields[name]
                old, new = line._display(field, current.get(name)), line._display(field, line.data.get(name))
                style = ' style="font-weight: bold;"' if old != new else ''
                rows.append(Markup('<tr%s><td>%s</td><td>%s</td><td>%s</td></tr>') % (
                    Markup(style), field._description_string(self.env), old, new))
            line.review_html = Markup(
                '<table class="table table-sm"><thead><tr><th>%s</th><th>%s</th><th>%s</th></tr></thead>'
                '<tbody>%s</tbody></table>') % (
                self.env._('Field'), self.env._('Now'), self.env._('Given'), Markup('').join(rows))

    def _display(self, field, value):
        if value in (False, None, ''):
            return ''
        if field.type == 'many2one':
            return escape(self.env[field.comodel_name].sudo().browse(value).display_name)
        if field.type == 'selection':
            return escape(dict(field._description_selection(self.env)).get(value, value))
        return escape(str(value))

    # ------------------------------------------------------------------
    # The new hire answering, from the website
    # ------------------------------------------------------------------

    def _check_open(self):
        self.ensure_one()
        if self.preboarding_id.state != 'running':
            raise UserError(self.env._('Your pre-boarding is closed.'))
        if self.state in ('done', 'submitted'):
            raise UserError(self.env._('This step is already done.'))

    def _clean_values(self, raw):
        """ :return: the values of the form, checked and converted, by field name """
        self.ensure_one()
        model, names = self._fields_of_kind()
        values = {}
        for name in names:
            field = model._fields[name]
            text = (raw.get(name) or '').strip()
            label = field._description_string(self.env)
            if not text:
                values[name] = False
                continue
            if field.type == 'many2one':
                record = self.env[field.comodel_name].sudo().browse(int(text) if text.isdigit() else 0).exists()
                if not record:
                    raise UserError(self.env._('Choose a value of the list for %s.', label))
                values[name] = record.id
            elif field.type == 'date':
                try:
                    values[name] = fields.Date.to_string(fields.Date.to_date(text))
                except ValueError:
                    raise UserError(self.env._('%s is not a date.', label)) from None
            elif field.type == 'integer':
                if not text.isdigit():
                    raise UserError(self.env._('%s is a number.', label))
                values[name] = int(text)
            elif field.type == 'selection':
                if text not in dict(field._description_selection(self.env)):
                    raise UserError(self.env._('Choose a value of the list for %s.', label))
                values[name] = text
            else:
                values[name] = text[:256]
        if self.kind == 'bank' and not values.get('account_number'):
            raise UserError(self.env._('Give the account number.'))
        return values

    def _submit(self, raw=None):
        """ The new hire answers the step: a form reviewed by HR, or a step to read or do, done at once. """
        self.ensure_one()
        self._check_open()
        if self.kind in self.env['hr.preboarding.step']._auto_kinds():
            raise UserError(self.env._('%s is done by itself once you did what it asks.', self.name))
        if not self.needs_review:
            self.sudo().write({'state': 'done', 'date_done': fields.Datetime.now()})
            self.preboarding_id._check_done()
            return
        values = self._clean_values(raw or {})
        self.sudo().write({'data': values, 'state': 'submitted', 'review_note': False})
        preboarding = self.preboarding_id.sudo()
        preboarding.activity_schedule(
            'mail.mail_activity_data_todo', user_id=preboarding.create_uid.id,
            summary=self.env._('Review: %s', self.name), note=self.env._('%(employee)s gave the %(step)s.',
                                                                        employee=self.employee_id.name,
                                                                        step=self.name))

    def _refresh(self):
        """ Hook: mark done the steps another record completes; the bridges extend it. """

    def _on_started(self):
        """ Hook: the pre-boarding of the steps started, e.g. to create the documents to upload. """

    def _mark_done(self):
        self.sudo().write({'state': 'done', 'date_done': fields.Datetime.now()})
        self.preboarding_id._check_done()

    # ------------------------------------------------------------------
    # HR reviewing
    # ------------------------------------------------------------------

    def _check_reviewer(self):
        if not self.env.su and not self.env.user.has_group('hr.group_hr_user'):
            raise UserError(self.env._('Only HR reviews what the new hires give.'))

    def action_apply(self):
        """ Write what the new hire gave on the employee. """
        self._check_reviewer()
        for line in self:
            if line.state != 'submitted':
                raise UserError(self.env._('%s is not waiting for a review.', line.name))
            # a field left blank keeps what the employee has
            values = {key: value for key, value in (line.data or {}).items() if value not in (False, None, '')}
            employee = line.employee_id
            if line.kind == 'bank':
                partner = employee.sudo().work_contact_id
                account = self.env['res.partner.bank'].sudo().create({
                    **values,
                    'partner_id': partner.id,
                    'holder_name': values.get('holder_name') or employee.name,
                })
                employee.sudo().bank_account_ids = [(4, account.id)]
            else:
                employee.sudo().write(values)
            line.sudo().write({'state': 'done', 'date_done': fields.Datetime.now()})
            line.preboarding_id.activity_feedback(['mail.mail_activity_data_todo'],
                                                  feedback=self.env._('%s applied.', line.name))
        self.preboarding_id._check_done()
        return True

    def action_send_back(self, note=False):
        """ Ask the new hire to correct what they gave. """
        self._check_reviewer()
        for line in self:
            if line.state != 'submitted':
                raise UserError(self.env._('%s is not waiting for a review.', line.name))
            line.sudo().write({'state': 'returned', 'review_note': note or False})
            preboarding = line.preboarding_id
            partner = preboarding.employee_id.user_id.partner_id or preboarding.employee_id.work_contact_id
            preboarding.sudo().message_notify(
                partner_ids=partner.ids, subject=self.env._('Please check: %s', line.name),
                body=self.env._('HR asks you to check %(step)s: %(note)s %(url)s', step=line.name, note=note or '',
                                url=preboarding._get_url()),
                email_layout_xmlid='mail.mail_notification_light')
        return True

    def action_open_send_back(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Send Back'),
            'res_model': 'hr.preboarding.send.back',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_line_id': self.id},
        }
