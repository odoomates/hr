from odoo import fields, models


class HrExitChecklist(models.Model):
    """ What has to be cleared before an employee leaves, and who clears it, e.g. the manager getting the laptop
        back. Each approved exit gets a clearance line per item. """
    _name = 'hr.exit.checklist'
    _description = 'Exit Checklist Item'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company')
    description = fields.Text(translate=True)
    responsible_type = fields.Selection([
        ('manager', 'Manager of the Employee'),
        ('department', 'Manager of the Department'),
        ('hr_responsible', 'HR Responsible of the Contract'),
        ('group', 'Users of a Group'),
        ('user', 'Given Users'),
    ], string='Cleared By', required=True, default='manager')
    group_id = fields.Many2one('res.groups')
    user_ids = fields.Many2many('res.users', string='Users')
    departure_reason_ids = fields.Many2many(
        'hr.departure.reason', string='Only For', help='The departure reasons the item applies to. Empty: all.')

    def _get_responsibles(self, employee):
        """ :return: the users clearing the item for `employee`, the HR administrators when nobody is found """
        self.ensure_one()
        employee = employee.sudo()
        if self.responsible_type == 'manager':
            users = employee.parent_id.user_id
        elif self.responsible_type == 'department':
            users = employee.department_id.manager_id.user_id
        elif self.responsible_type == 'hr_responsible':
            users = employee.version_id.hr_responsible_id
        elif self.responsible_type == 'group':
            users = self.group_id.all_user_ids
        else:
            users = self.user_ids
        users = users.filtered(lambda user: user.active and not user.share and user != employee.user_id)
        return users or self.env.ref('hr.group_hr_manager').all_user_ids.filtered(
            lambda user: user.active and not user.share)
