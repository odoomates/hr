from odoo import fields, models
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    preboarding_ids = fields.One2many('hr.preboarding', 'employee_id', string='Pre-boardings',
                                      groups='hr.group_hr_user')
    preboarding_state = fields.Selection(related='preboarding_ids.state', string='Pre-boarding',
                                         groups='hr.group_hr_user')

    def action_start_preboarding(self):
        """ Invite the new hire to their pre-boarding on the website, before their first day. """
        self.ensure_one()
        if not self.env.user.has_group('hr.group_hr_user'):
            raise UserError(self.env._('Only HR starts the pre-boarding of a new hire.'))
        return self.env['hr.preboarding']._start(self)._open()

    def action_open_preboarding(self):
        self.ensure_one()
        return self.preboarding_ids[:1]._open()
