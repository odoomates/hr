from odoo import _, api, fields, models

CONDITIONS = [('new', 'New'), ('good', 'Good'), ('fair', 'Fair'), ('damaged', 'Damaged')]


class OmHrAssetAssignment(models.Model):
    """ An asset in the hands of an employee, from the day it is handed over to the day it comes back or is lost.

    The current holder stays the employee of the equipment in core Maintenance: every change of it, made here or
    on the equipment, closes the assignment in progress and opens the next one.
    """
    _name = 'om.hr.asset.assignment'
    _inherit = ['mail.thread']
    _description = 'Asset Assignment'
    _order = 'date_from desc, id desc'
    _rec_name = 'equipment_id'

    equipment_id = fields.Many2one('maintenance.equipment', string='Asset', required=True, index=True,
                                   ondelete='cascade', tracking=True)
    category_id = fields.Many2one(related='equipment_id.category_id', store=True, string='Category')
    serial_no = fields.Char(related='equipment_id.serial_no', string='Serial Number')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, index=True, tracking=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    date_from = fields.Date(string='Handed Over On', required=True, default=fields.Date.context_today,
                            tracking=True)
    date_to = fields.Date(string='Returned On', tracking=True)
    condition_out = fields.Selection(CONDITIONS, string='Condition Handed Over', default='good')
    condition_in = fields.Selection(CONDITIONS, string='Condition Returned')
    condition_out_label = fields.Char(compute='_compute_condition_labels')
    condition_in_label = fields.Char(compute='_compute_condition_labels')
    handed_by_id = fields.Many2one('res.users', string='Handed Over By', default=lambda self: self.env.user)
    received_by_id = fields.Many2one('res.users', string='Received By')
    state = fields.Selection([
        ('assigned', 'Assigned'),
        ('returned', 'Returned'),
        ('lost', 'Lost'),
    ], required=True, default='assigned', index=True, tracking=True)
    charge_amount = fields.Monetary(
        string='Charge to Employee', tracking=True,
        help='What the employee pays for the asset lost or damaged. With the payroll, it is deducted from their '
             'next payslip.')
    note = fields.Text()

    @api.depends('condition_out', 'condition_in')
    def _compute_condition_labels(self):
        """ The conditions as words, for the handover form. """
        labels = dict(self._fields['condition_out']._description_selection(self.env))
        for assignment in self:
            assignment.condition_out_label = labels.get(assignment.condition_out, '')
            assignment.condition_in_label = labels.get(assignment.condition_in, '')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            equipment = self.env['maintenance.equipment'].browse(vals.get('equipment_id'))
            if equipment.company_id and 'company_id' not in vals:
                vals['company_id'] = equipment.company_id.id
        return super().create(vals_list)

    def _close(self, state='returned', date=None, condition=False, note=False, charge=0.0):
        """ The asset comes back, or is lost: the assignment ends. """
        values = {
            'state': state,
            'date_to': date or fields.Date.context_today(self),
            'received_by_id': self.env.user.id if state == 'returned' else False,
        }
        if condition:
            values['condition_in'] = condition
        if charge:
            values['charge_amount'] = charge
        for assignment in self:
            assignment.write(dict(values, note='\n'.join(filter(None, [assignment.note, note])) or False))
        self._on_closed()

    def _on_closed(self):
        """ Hook: the assignments are returned or lost. """

    def action_print_handover(self):
        self.ensure_one()
        template = self.env.ref('om_hr_asset.print_template_handover', raise_if_not_found=False)
        if not template or not template.ref_ir_act_window:
            return False
        action = template.ref_ir_act_window._get_action_dict()
        action['context'] = {'active_model': self._name, 'active_ids': self.ids, 'active_id': self.id,
                             'default_template_id': template.id}
        return action
