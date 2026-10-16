from odoo import api, fields, models
from odoo.exceptions import UserError

from ..models.hr_asset_assignment import CONDITIONS


class HrAssetWizard(models.TransientModel):
    """ Hand an asset over to an employee, take it back, or report it lost. """
    _name = 'hr.asset.wizard'
    _description = 'Assign or Return an Asset'

    mode = fields.Selection([('assign', 'Assign'), ('return', 'Return'), ('lost', 'Report Lost')], required=True)
    equipment_id = fields.Many2one('maintenance.equipment', string='Asset', required=True)
    employee_id = fields.Many2one('hr.employee')
    current_employee_id = fields.Many2one(related='equipment_id.employee_id', string='Held By')
    company_id = fields.Many2one(related='equipment_id.company_id')
    currency_id = fields.Many2one('res.currency', compute='_compute_currency_id')
    date = fields.Date(required=True, default=fields.Date.context_today)
    condition = fields.Selection(CONDITIONS, default='good')
    charge_amount = fields.Monetary(string='Charge to Employee',
                                    help='What the employee pays for the asset lost or damaged.')
    request_maintenance = fields.Boolean(string='Request a Repair',
                                         help='Create a maintenance request for the damaged asset.')
    note = fields.Text()

    @api.depends('company_id')
    def _compute_currency_id(self):
        for wizard in self:
            wizard.currency_id = (wizard.company_id or self.env.company).currency_id

    def action_confirm(self):
        self.ensure_one()
        equipment = self.equipment_id
        if self.mode == 'assign':
            if not self.employee_id:
                raise UserError(self.env._('Choose the employee receiving %s.', equipment.name))
            if equipment.lost:
                raise UserError(self.env._('%s is reported lost.', equipment.name))
            note = self.env._('Handed over to %s.', self.employee_id.name)
            equipment._open_assignments().sudo()._close(date=self.date, note=note)
            equipment.with_context(om_asset_no_log=True).write({
                'employee_id': self.employee_id.id, 'equipment_assign_to': 'employee'})
            assignment = equipment._open_assignment({
                'date_from': self.date, 'condition_out': self.condition, 'note': self.note,
                'handed_by_id': self.env.user.id})
            return assignment.action_print_handover() or True
        open_assignments = equipment._open_assignments()
        if not open_assignments:
            raise UserError(self.env._('%s is not assigned.', equipment.name))
        if self.mode == 'return':
            open_assignments._close('returned', self.date, self.condition, self.note, self.charge_amount)
            equipment.with_context(om_asset_no_log=True).employee_id = False
            if self.condition == 'damaged' and self.request_maintenance:
                self.env['maintenance.request'].create({
                    'name': self.env._('Repair %s', equipment.name),
                    'equipment_id': equipment.id,
                    'description': self.note,
                })
        else:
            open_assignments._close('lost', self.date, False, self.note, self.charge_amount)
            equipment.with_context(om_asset_no_log=True).write({
                'employee_id': False, 'lost': True, 'scrap_date': self.date})
            equipment.message_post(body=self.env._('Reported lost by %(user)s while held by %(employee)s.',
                                                   user=self.env.user.name, employee=open_assignments.employee_id.name))
        return True
