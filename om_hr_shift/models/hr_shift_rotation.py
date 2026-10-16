from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OmHrShiftRotation(models.Model):
    """ A cycle of shifts and days off, e.g. 2 mornings, 2 nights, 2 days off, repeated over the roster. """
    _name = 'om.hr.shift.rotation'
    _description = 'Shift Rotation'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    line_ids = fields.One2many('om.hr.shift.rotation.line', 'rotation_id', string='Days', copy=True)
    cycle_days = fields.Integer(compute='_compute_cycle_days', string='Days in the Cycle')
    pattern = fields.Char(compute='_compute_cycle_days')

    @api.depends('line_ids.template_id')
    def _compute_cycle_days(self):
        for rotation in self:
            rotation.cycle_days = len(rotation.line_ids)
            rotation.pattern = ' '.join(line.template_id.code or '-' for line in rotation.line_ids)

    @api.constrains('line_ids')
    def _check_lines(self):
        for rotation in self:
            if not rotation.line_ids.template_id:
                raise ValidationError(_('The rotation %s works one shift at least.', rotation.name))


class OmHrShiftRotationLine(models.Model):
    _name = 'om.hr.shift.rotation.line'
    _description = 'Shift Rotation Day'
    _order = 'rotation_id, sequence, id'

    rotation_id = fields.Many2one('om.hr.shift.rotation', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    template_id = fields.Many2one('om.hr.shift.template', string='Shift', help='Empty for a day off.')
