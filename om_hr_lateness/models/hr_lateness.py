from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrLateness(models.Model):
    """ A late arrival or an early departure of an employee on a working day, against the working schedule minus the
    time off and the public holidays. """
    _name = 'hr.lateness'
    _description = 'Lateness'
    _order = 'date desc, employee_id, kind'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one(related='employee_id.company_id', store=True, index=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    date = fields.Date(required=True, index=True)
    kind = fields.Selection([('late_in', 'Late Arrival'), ('early_out', 'Early Departure')], required=True)
    scheduled_at = fields.Datetime(string='Scheduled', required=True)
    actual_at = fields.Datetime(string='Actual', required=True)
    minutes = fields.Integer(required=True, aggregator='sum')
    attendance_id = fields.Many2one('hr.attendance', string='Attendance', ondelete='set null')
    policy_id = fields.Many2one('hr.lateness.policy', string='Policy', ondelete='set null')
    state = fields.Selection([('counted', 'Counted'), ('excused', 'Excused')], required=True, default='counted',
                             index=True)
    excuse_reason = fields.Char(string='Excuse')
    occurrence = fields.Integer(help='The time in the month the employee is late in this way, the excused ones not '
                                     'counted.')
    policy_line_id = fields.Many2one('hr.lateness.policy.line', string='Penalty Rule', ondelete='set null')
    penalty = fields.Selection(related='policy_line_id.penalty', store=True)
    warned = fields.Boolean(copy=False)

    _employee_day_kind_uniq = models.Constraint('UNIQUE(employee_id, date, kind)',
                                                'An employee is late once a day in each way.')

    @api.depends('employee_id', 'date', 'kind', 'minutes')
    def _compute_display_name(self):
        kinds = dict(self._fields['kind'].selection)
        for lateness in self:
            lateness.display_name = _('%(employee)s, %(kind)s of %(minutes)s min on %(date)s',
                                      employee=lateness.employee_id.name, kind=kinds.get(lateness.kind),
                                      minutes=lateness.minutes, date=lateness.date)

    # ------------------------------------------------------------------
    # Review
    # ------------------------------------------------------------------

    def _check_can_review(self):
        user = self.env.user
        if user.has_group('hr_attendance.group_hr_attendance_user'):
            return
        if user.has_group('hr_attendance.group_hr_attendance_officer') and all(
                lateness.sudo().employee_id.attendance_manager_id == user for lateness in self):
            return
        raise UserError(_('Only the attendance manager of the employee, or the attendance officers, excuse a '
                          'lateness.'))

    def _excuse(self, reason):
        self._check_can_review()
        if not reason:
            raise UserError(_('Give the reason of the excuse.'))
        self.sudo().write({'state': 'excused', 'excuse_reason': reason})
        self.sudo()._evaluate_months()
        return True

    def action_open_excuse(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Excuse'),
            'res_model': 'hr.lateness.excuse',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_lateness_ids': self.ids},
        }

    def action_count_again(self):
        self._check_can_review()
        self.sudo().write({'state': 'counted', 'excuse_reason': False})
        self.sudo()._evaluate_months()
        return True

    # ------------------------------------------------------------------
    # Occurrences and penalties
    # ------------------------------------------------------------------

    def _evaluate_months(self):
        """ Number the latenesses of the months of these, kind by kind, and give each its penalty. """
        months = {(lateness.employee_id, lateness.date.replace(day=1)) for lateness in self}
        for employee, month in months:
            self.env['hr.lateness']._evaluate(employee, month)

    @api.model
    def _evaluate(self, employee, month):
        next_month = fields.Date.add(month, months=1)
        latenesses = self.sudo().search([('employee_id', '=', employee.id), ('date', '>=', month),
                                         ('date', '<', next_month)], order='date, id')
        counts = {}
        for lateness in latenesses:
            if lateness.state == 'excused' or not lateness.policy_id:
                values = {'occurrence': 0, 'policy_line_id': False}
            else:
                counts[lateness.kind] = counts.get(lateness.kind, 0) + 1
                line = lateness.policy_id._line_for(lateness.kind, lateness.minutes, counts[lateness.kind])
                values = {'occurrence': counts[lateness.kind], 'policy_line_id': line.id}
            if any(lateness[name] != (value if name != 'policy_line_id' else lateness.policy_line_id.browse(value))
                   for name, value in values.items()):
                lateness.write(values)
        latenesses.filtered(lambda l: l.penalty == 'warning' and not l.warned)._warn()

    def _warn(self):
        """ A message to the employee, on their own chatter of the lateness. """
        for lateness in self:
            partner = lateness.employee_id.user_id.partner_id
            if partner:
                lateness.employee_id.message_post(
                    body=_('Warning: %(lateness)s. Please keep to your working hours.', lateness=lateness.display_name),
                    partner_ids=partner.ids, subtype_xmlid='mail.mt_note')
            lateness.warned = True
