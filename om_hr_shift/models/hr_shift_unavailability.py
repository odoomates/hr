from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrShiftUnavailability(models.Model):
    """ Days an employee cannot work, for the planners to see on the roster. """
    _name = 'hr.shift.unavailability'
    _description = 'Unavailability'
    _check_company_auto = True
    _order = 'date_from desc'

    employee_id = fields.Many2one('hr.employee', required=True, index=True, ondelete='cascade',
                                  default=lambda self: self.env.user.employee_id, check_company=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    date_from = fields.Date(string='From', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='To', required=True, default=fields.Date.context_today)
    reason = fields.Char()

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for unavailability in self:
            if unavailability.date_to < unavailability.date_from:
                raise ValidationError(self.env._('An unavailability ends after it starts.'))
