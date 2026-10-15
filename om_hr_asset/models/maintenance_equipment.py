from odoo import _, api, fields, models


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    om_assignment_ids = fields.One2many('om.hr.asset.assignment', 'equipment_id', string='Assignments')
    om_assignment_count = fields.Integer(compute='_compute_om_assignment_count')
    om_lost = fields.Boolean(string='Lost', copy=False, tracking=True)
    om_asset_state = fields.Selection([
        ('available', 'Available'),
        ('assigned', 'Assigned'),
        ('lost', 'Lost'),
    ], string='Asset Status', compute='_compute_om_asset_state', store=True)

    @api.depends('om_assignment_ids')
    def _compute_om_assignment_count(self):
        for equipment in self:
            equipment.om_assignment_count = len(equipment.om_assignment_ids)

    @api.depends('employee_id', 'om_lost')
    def _compute_om_asset_state(self):
        for equipment in self:
            equipment.om_asset_state = 'lost' if equipment.om_lost else \
                'assigned' if equipment.employee_id else 'available'

    @api.model_create_multi
    def create(self, vals_list):
        equipments = super().create(vals_list)
        equipments.filtered('employee_id')._om_open_assignment()
        return equipments

    def write(self, vals):
        if 'employee_id' not in vals or self.env.context.get('om_asset_no_log'):
            return super().write(vals)
        holders = {equipment: equipment.employee_id for equipment in self}
        result = super().write(vals)
        for equipment, previous in holders.items():
            if equipment.employee_id == previous:
                continue
            equipment._om_open_assignments().sudo()._close(note=_('Unassigned from the asset.'))
            if equipment.employee_id:
                equipment._om_open_assignment()
        return result

    def _om_open_assignments(self):
        return self.env['om.hr.asset.assignment'].search(
            [('equipment_id', 'in', self.ids), ('state', '=', 'assigned')])

    def _om_open_assignment(self, values=None):
        """ The assignment of the asset to its employee, from today unless told otherwise. """
        return self.env['om.hr.asset.assignment'].sudo().create([{
            'equipment_id': equipment.id,
            'employee_id': equipment.employee_id.id,
            **(values or {}),
        } for equipment in self])

    def _om_open_wizard(self, mode):
        self.ensure_one()
        titles = {'assign': _('Assign %s', self.name), 'return': _('Return %s', self.name),
                  'lost': _('Report %s Lost', self.name)}
        return {
            'type': 'ir.actions.act_window',
            'name': titles[mode],
            'res_model': 'om.hr.asset.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_equipment_id': self.id, 'default_mode': mode},
        }

    def action_om_assign(self):
        return self._om_open_wizard('assign')

    def action_om_return(self):
        return self._om_open_wizard('return')

    def action_om_lost(self):
        return self._om_open_wizard('lost')

    def action_om_found(self):
        """ A lost asset turns up again: it is available. """
        self.write({'om_lost': False, 'scrap_date': False})
        return True

    def action_om_open_assignments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('History of %s', self.name),
            'res_model': 'om.hr.asset.assignment',
            'view_mode': 'list,form',
            'domain': [('equipment_id', '=', self.id)],
            'context': {'create': False},
        }
