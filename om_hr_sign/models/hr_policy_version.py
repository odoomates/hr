import hashlib

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# what a published version keeps as it was published
FROZEN_FIELDS = {'content_type', 'body', 'document_file', 'document_filename', 'policy_id'}


class HrPolicyVersion(models.Model):
    """ The text of a policy at a time: written in the editor or a PDF file. Published, it is asked to every
    employee of the policy; the next version published replaces it and asks everyone again. """
    _name = 'hr.policy.version'
    _description = 'Policy Version'
    _order = 'policy_id, number desc'

    policy_id = fields.Many2one('hr.policy', required=True, ondelete='cascade', index=True)
    number = fields.Integer(string='Version', readonly=True, copy=False)
    name = fields.Char(compute='_compute_name')
    content_type = fields.Selection([
        ('text', 'Text'),
        ('pdf', 'PDF File'),
    ], string='Content', required=True, default='text')
    body = fields.Html(string='Text', sanitize_style=True)
    document_file = fields.Binary(string='PDF', attachment=True)
    document_filename = fields.Char()
    change_note = fields.Text(string='What Changed')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('superseded', 'Replaced'),
    ], required=True, default='draft', readonly=True, copy=False, index=True)
    date_published = fields.Datetime(string='Published On', readonly=True, copy=False)
    published_by_id = fields.Many2one('res.users', string='Published By', readonly=True, copy=False)
    document_hash = fields.Char(string='Fingerprint', readonly=True, copy=False,
                                help='SHA-256 of the version as published.')
    assignment_ids = fields.One2many('hr.policy.assignment', 'version_id', string='Answers')
    company_id = fields.Many2one(related='policy_id.company_id', store=True, index=True)

    @api.depends('policy_id.name', 'number')
    def _compute_name(self):
        for version in self:
            version.name = _('%(policy)s, version %(number)s', policy=version.policy_id.name, number=version.number)

    @api.model_create_multi
    def create(self, vals_list):
        versions = super().create(vals_list)
        for version in versions:
            others = version.policy_id.version_ids - version
            version.number = max(others.mapped('number'), default=0) + 1
        return versions

    def write(self, vals):
        if FROZEN_FIELDS & set(vals) and not self.env.su and any(v.state != 'draft' for v in self):
            raise UserError(_('A published version stays as it was published: write a new version instead.'))
        return super().write(vals)

    def unlink(self):
        if any(version.state != 'draft' for version in self):
            raise UserError(_('Only a draft version can be deleted.'))
        return super().unlink()

    def _get_pdf(self):
        """ :return: the version as a PDF, to sign """
        self.ensure_one()
        if self.content_type == 'pdf':
            data = self.sudo().document_file
            return data.content if data else b''
        return self.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'om_hr_sign.action_report_policy_version', res_ids=self.ids)[0]

    def _get_content_bytes(self):
        self.ensure_one()
        if self.content_type == 'pdf':
            data = self.sudo().document_file
            return data.content if data else b''
        return (self.body or '').encode()

    def action_publish(self):
        """ Replace the current version and ask everyone the policy reaches. """
        for version in self:
            if version.state != 'draft':
                raise UserError(_('%s is already published.', version.name))
            content = version._get_content_bytes()
            if version.content_type == 'pdf' and not content.startswith(b'%PDF'):
                raise UserError(_('Upload the PDF of %s.', version.name))
            if version.content_type == 'text' and not version.body:
                raise UserError(_('Write the text of %s.', version.name))
            previous = version.policy_id.version_ids.filtered(lambda v: v.state == 'published')
            previous.sudo().write({'state': 'superseded'})
            previous.assignment_ids.filtered(lambda a: a.state == 'pending')._cancel()
            version.sudo().write({
                'state': 'published',
                'date_published': fields.Datetime.now(),
                'published_by_id': self.env.uid,
                'document_hash': hashlib.sha256(content).hexdigest(),
            })
            version._assign(version.policy_id._audience())
            version.policy_id.message_post(
                body=_('%(version)s published: %(count)s employees asked.', version=version.name,
                       count=len(version.assignment_ids)),
                subtype_xmlid='mail.mt_note')
        return True

    def _assign(self, employees):
        """ Ask `employees` this version, unless they were already. """
        self.ensure_one()
        employees -= self.sudo().assignment_ids.employee_id
        if not employees:
            return self.env['hr.policy.assignment']
        today = fields.Date.context_today(self)
        due = fields.Date.add(today, days=self.policy_id.due_days) if self.policy_id.due_days else False
        assignments = self.env['hr.policy.assignment'].sudo().create([{
            'version_id': self.id,
            'employee_id': employee.id,
            'date_due': due,
        } for employee in employees])
        assignments._start()
        return assignments

    def action_open(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }
