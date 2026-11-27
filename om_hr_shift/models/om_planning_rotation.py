from odoo import api, fields, models


class OmPlanningRotation(models.Model):
    _inherit = 'om.planning.rotation'

    pattern = fields.Char(compute='_compute_pattern',
                          help='The short names of the shifts of the cycle, - for a day off.')
    old_rotation_id = fields.Integer(string='Former Shift Rotation', readonly=True, copy=False,
                                     index='btree_not_null')

    @api.depends('line_ids.template_id.code', 'line_ids.sequence')
    def _compute_pattern(self):
        for rotation in self:
            lines = rotation.line_ids.sorted(lambda line: (line.sequence, line.id or 0))
            rotation.pattern = ' '.join((line.template_id.code or line.template_id.name or '?')
                                        if line.template_id else '-' for line in lines)
