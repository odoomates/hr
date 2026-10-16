from odoo import api, fields, models
from odoo.exceptions import UserError


class HrPolicy(models.Model):
    """ A rule of the company the employees read and agree to, or sign, e.g. the code of conduct or an NDA.

    Its text changes from version to version: publishing a version asks every employee it reaches to answer it,
    and the employees who join later, or move into its audience, are asked too. """
    _name = 'hr.policy'
    _inherit = ['mail.thread', 'hr.audience.mixin']
    _description = 'Policy'
    _order = 'sequence, name, id'

    name = fields.Char(required=True, translate=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, tracking=True)
    answer_type = fields.Selection([
        ('acknowledge', 'Read and Agree'),
        ('sign', 'Signature'),
    ], string='Answer', required=True, default='acknowledge', tracking=True,
        help='Read and Agree: the employee agrees with one click, logged with the date and their address. '
             'Signature: the employee signs it through Sign and gets the signed PDF.')
    due_days = fields.Integer(string='Days to Answer', default=14,
                              help='The answer is due that many days after the employee is asked.')
    remind_days = fields.Integer(string='Remind Every', default=7,
                                 help='Days between the reminders to the employees who did not answer. 0 for none.')
    assign_new = fields.Boolean(
        string='Ask New Employees', default=True,
        help='The employees who join later, or move into the audience, e.g. to a department, are asked the current '
             'version too.')
    version_ids = fields.One2many('hr.policy.version', 'policy_id', string='Versions')
    version_id = fields.Many2one('hr.policy.version', string='Current Version', compute='_compute_version_id',
                                 store=True)
    assignment_ids = fields.One2many('hr.policy.assignment', 'policy_id', string='Answers')
    assignment_count = fields.Integer(compute='_compute_answers', string='Asked')
    done_count = fields.Integer(compute='_compute_answers', string='Answered')
    pending_count = fields.Integer(compute='_compute_answers', string='Waiting')
    done_rate = fields.Float(compute='_compute_answers', string='Answered (%)')

    @api.depends('version_ids.state')
    def _compute_version_id(self):
        for policy in self:
            policy.version_id = policy.version_ids.filtered(lambda version: version.state == 'published')[:1]

    @api.depends('version_id.assignment_ids.state')
    def _compute_answers(self):
        for policy in self:
            assignments = policy.sudo().version_id.assignment_ids.filtered(lambda a: a.state != 'cancelled')
            policy.assignment_count = len(assignments)
            policy.done_count = len(assignments.filtered(lambda a: a.state == 'done'))
            policy.pending_count = len(assignments.filtered(lambda a: a.state == 'pending'))
            policy.done_rate = policy.done_count / policy.assignment_count * 100 if policy.assignment_count else 0.0

    def action_new_version(self):
        """ A draft of the next version, its content copied from the current one. """
        self.ensure_one()
        if self.version_ids.filtered(lambda version: version.state == 'draft'):
            raise UserError(self.env._('%s already has a draft version: publish it or delete it first.', self.name))
        current = self.version_id
        version = self.env['hr.policy.version'].create({
            'policy_id': self.id,
            'content_type': current.content_type or 'text',
            'body': current.body,
            'document_file': current.document_file,
            'document_filename': current.document_filename,
        })
        return version.action_open()

    def action_open_assignments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Answers'),
            'res_model': 'hr.policy.assignment',
            'view_mode': 'list,pivot,form',
            'domain': [('policy_id', '=', self.id)],
            'context': {'create': False, 'search_default_current': 1},
        }
