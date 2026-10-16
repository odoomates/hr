from odoo import api, fields, models
from odoo.exceptions import UserError


class HrRequestCategory(models.Model):
    _name = 'hr.request.category'
    _description = 'HR Request Category'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company')
    description = fields.Text(translate=True, help='Shown to the employee writing a request of the category.')


class HrRequest(models.Model):
    """ What an employee asks HR for, approved along the approval flow of the HR requests. """
    _name = 'hr.request'
    _inherit = ['approval.mixin']
    _description = 'HR Request'
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
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    category_id = fields.Many2one(
        'hr.request.category', required=True, tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    category_description = fields.Text(related='category_id.description')
    date = fields.Date(required=True, default=fields.Date.context_today)
    description = fields.Text(string='Details')

    @api.depends('employee_id')
    def _compute_company_id(self):
        for request in self:
            request.company_id = request.employee_id.company_id or request.company_id or self.env.company

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', self.env._('New')) == self.env._('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.request') or self.env._('New')
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_submitted(self):
        if any(request.approval_state not in ('draft', 'cancel') for request in self):
            raise UserError(self.env._('Only a draft or a cancelled request can be deleted.'))

    def _approval_employee(self):
        self.ensure_one()
        return self.employee_id

    def _approval_check_requester(self):
        self.ensure_one()
        if self.employee_id.user_id != self.env.user and not self.env.user.has_group('hr.group_hr_user'):
            raise UserError(self.env._('Only %(employee)s or HR can change %(request)s.',
                                       employee=self.employee_id.name, request=self.name))
