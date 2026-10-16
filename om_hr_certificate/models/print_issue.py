from odoo import api, fields, models


class PrintIssue(models.Model):
    _inherit = 'print.issue'

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', compute='_compute_employee_id', store=True, index='btree_not_null')

    @api.depends('res_model', 'res_id')
    def _compute_employee_id(self):
        for issue in self:
            issue.employee_id = issue.res_id if issue.res_model == 'hr.employee' else False

    def _check_can_cancel(self):
        """ HR managers cancel the certificates of the employees. """
        if self.env.user.has_group('hr.group_hr_manager') and all(
                issue.res_model == 'hr.employee' for issue in self):
            return
        super()._check_can_cancel()
