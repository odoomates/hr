from odoo import _, api, fields, models


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'sign.mixin']

    policy_assignment_ids = fields.One2many('hr.policy.assignment', 'employee_id', string='Policies',
                                            groups='hr.group_hr_user')
    policy_pending_count = fields.Integer(compute='_compute_policy_counts', string='Policies to Answer',
                                          groups='hr.group_hr_user')

    def _compute_policy_counts(self):
        counts = dict(self.env['hr.policy.assignment']._read_group(
            [('employee_id', 'in', self.ids), ('state', '=', 'pending')], ['employee_id'], ['__count']))
        for employee in self:
            employee.policy_pending_count = counts.get(employee, 0)

    def _sign_request_domain(self):
        """ The requests about the employees, and those they sign. """
        return ['|', '&', ('res_model', '=', self._name), ('res_id', 'in', self.ids),
                ('signer_ids.partner_id', 'in', self.work_contact_id.ids)]

    def _compute_sign_request_count(self):
        Request = self.env['sign.request']
        for employee in self:
            employee.sign_request_count = Request.search_count(employee._sign_request_domain())

    def action_open_sign_requests(self):
        action = super().action_open_sign_requests()
        action['domain'] = self._sign_request_domain()
        return action

    def _sign_default_signers(self):
        return [(10, _('Employee'), self.work_contact_id)] if self.work_contact_id else []

    def action_open_policy_assignments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Policies'),
            'res_model': 'hr.policy.assignment',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'create': False},
        }

    # ------------------------------------------------------------------
    # The policies of new employees, and of those moving into an audience
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        employees._assign_policies()
        return employees

    def write(self, vals):
        result = super().write(vals)
        if {'department_id', 'job_id', 'category_ids', 'company_id'} & set(vals):
            self._assign_policies()
        if vals.get('active') is False:
            pending = self.env['hr.policy.assignment'].sudo().search(
                [('employee_id', 'in', self.ids), ('state', '=', 'pending')])
            pending._cancel()
        return result

    def _assign_policies(self):
        """ Ask the employees the current version of the policies they are now reached by. """
        employees = self.filtered('active')
        if not employees:
            return
        versions = self.env['hr.policy.version'].sudo().search([
            ('state', '=', 'published'), ('policy_id.active', '=', True), ('policy_id.assign_new', '=', True)])
        for version in versions:
            version._assign(version.policy_id._in_audience(employees))
