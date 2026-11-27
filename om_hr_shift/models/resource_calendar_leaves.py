from odoo import api, fields, models


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    shift_unavailability = fields.Boolean(
        string='Unavailability', help='A period the employee told they cannot work, for the shift planners.')
    old_unavailability_id = fields.Integer(string='Former Unavailability', readonly=True, copy=False,
                                           index='btree_not_null')

    @api.model
    def default_get(self, fields):
        values = super().default_get(fields)
        if self.env.context.get('om_hr_shift_my_unavailability') and 'resource_id' in fields:
            employee = self.env.user.employee_id
            if employee:
                values['resource_id'] = employee.resource_id.id
        return values
