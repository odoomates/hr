from odoo import api, fields, models
from odoo.exceptions import UserError


class HrAppraisalCalibration(models.Model):
    """ HR and the managers review the ratings and the potentials of a cycle together, on the 9-box grid, and
    adjust them: each change is logged with who made it and why. """
    _name = 'hr.appraisal.calibration'
    _inherit = ['mail.thread']
    _description = 'Calibration Session'
    _check_company_auto = True
    _order = 'date desc, id desc'

    name = fields.Char(required=True, tracking=True)
    cycle_id = fields.Many2one('hr.appraisal.cycle', index=True, check_company=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    user_ids = fields.Many2many('res.users', string='Participants', domain=[('share', '=', False)])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'In Session'),
        ('done', 'Closed'),
    ], required=True, default='draft', copy=False, tracking=True)
    appraisal_ids = fields.Many2many('hr.appraisal', string='Appraisals', check_company=True,
                                     domain="[('state', 'in', ('review', 'done'))]")
    log_ids = fields.One2many('hr.appraisal.calibration.log', 'calibration_id', string='Changes', readonly=True)
    log_count = fields.Integer(compute='_compute_log_count')
    note = fields.Html(string='Notes')

    @api.depends('log_ids')
    def _compute_log_count(self):
        for session in self:
            session.log_count = len(session.log_ids)

    def action_load_appraisals(self):
        """ The appraisals of the cycle under review or done, to calibrate. """
        for session in self:
            if not session.cycle_id:
                raise UserError(self.env._('Choose the cycle of %s first.', session.name))
            session.appraisal_ids |= session.cycle_id.appraisal_ids.filtered(
                lambda appraisal: appraisal.state in ('review', 'done'))
        return True

    def action_start(self):
        self.write({'state': 'running'})
        return True

    def action_close(self):
        self.write({'state': 'done'})
        return True

    def action_reset(self):
        self.write({'state': 'draft'})
        return True

    def action_open_grid(self):
        """ The appraisals of the session on the 9-box grid: potential up, performance across. """
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('om_hr_appraisal.om_hr_appraisal_action_nine_box')
        action['domain'] = [('id', 'in', self.appraisal_ids.ids)]
        action['display_name'] = self.env._('9-Box: %s', self.name)
        return action


class HrAppraisalCalibrationLog(models.Model):
    """ A rating or a potential changed in a calibration session. """
    _name = 'hr.appraisal.calibration.log'
    _description = 'Calibration Change'
    _order = 'create_date desc, id desc'

    calibration_id = fields.Many2one('hr.appraisal.calibration', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one(related='calibration_id.company_id', store=True)
    appraisal_id = fields.Many2one('hr.appraisal', required=True, ondelete='cascade')
    employee_id = fields.Many2one(related='appraisal_id.employee_id', store=True)
    what = fields.Selection([('rating', 'Rating'), ('potential', 'Potential')], required=True)
    old_value = fields.Char(string='From')
    new_value = fields.Char(string='To')
    user_id = fields.Many2one('res.users', string='By', required=True, default=lambda self: self.env.user)
    reason = fields.Text(required=True)

