from odoo import fields, models


class HrPreboardingSendBack(models.TransientModel):
    """ Ask a new hire to correct a step, with a note. """
    _name = 'hr.preboarding.send.back'
    _description = 'Send a Pre-boarding Step Back'

    line_id = fields.Many2one('hr.preboarding.line', required=True, ondelete='cascade')
    note = fields.Text(required=True, help='What to correct, sent to the new hire.')

    def action_send_back(self):
        self.ensure_one()
        return self.line_id.action_send_back(self.note)
