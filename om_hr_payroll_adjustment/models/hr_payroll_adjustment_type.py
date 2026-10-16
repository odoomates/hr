from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OmHrPayrollAdjustmentType(models.Model):
    """ A kind of addition to or deduction from the pay, e.g. a bonus or a fine: it has its own salary rule, kept in
    sync by the type, so that the payslips show each kind on its own line. """
    _name = 'om.hr.payroll.adjustment.type'
    _description = 'Payroll Adjustment Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, help='The code of the salary rule and of its input, e.g. ADJ_BONUS.')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    kind = fields.Selection([('addition', 'Addition'), ('deduction', 'Deduction')], required=True,
                            default='addition')
    category_id = fields.Many2one(
        'hr.salary.rule.category', string='Category', required=True,
        default=lambda self: self.env.ref('om_hr_payroll.ALW', raise_if_not_found=False),
        help='Where the payslip counts it: an allowance is part of the gross, a deduction comes off it.')
    structure_ids = fields.Many2many(
        'hr.payroll.structure', string='Salary Structures',
        default=lambda self: self.env.ref('om_hr_payroll.structure_base', raise_if_not_found=False),
        help='The structures paying this kind of adjustment.')
    require_approval = fields.Boolean(string='Needs Approval', default=True,
                                      help='An adjustment of this type runs once approved along the approval flow.')
    settle_at_exit = fields.Boolean(
        string='Settle at Exit', help='The final settlement of an employee leaving takes everything still due.')
    rule_id = fields.Many2one('hr.salary.rule', string='Salary Rule', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', string='Company',
                                 help='Leave empty to share the type with all the companies.')
    description = fields.Text(translate=True)

    _code_uniq = models.Constraint('UNIQUE(code)', 'Each adjustment type has its own code.')

    @api.onchange('kind')
    def _onchange_kind(self):
        code = 'DED' if self.kind == 'deduction' else 'ALW'
        self.category_id = self.env.ref('om_hr_payroll.%s' % code, raise_if_not_found=False)
        self.settle_at_exit = self.kind == 'deduction'

    @api.constrains('code')
    def _check_code(self):
        for adjustment_type in self:
            if not adjustment_type.code.replace('_', '').isalnum() or adjustment_type.code[0].isdigit():
                raise ValidationError(_('The code %s is used in the salary rules: letters, digits and _ only, '
                                        'not starting with a digit.', adjustment_type.code))

    @api.model_create_multi
    def create(self, vals_list):
        types = super().create(vals_list)
        types._sync_rule()
        return types

    def write(self, vals):
        old_structures = {adjustment_type: adjustment_type.structure_ids for adjustment_type in self}
        result = super().write(vals)
        if {'name', 'code', 'kind', 'category_id', 'structure_ids', 'active', 'company_id'} & set(vals):
            self._sync_rule(old_structures)
        return result

    def unlink(self):
        rules = self.rule_id.sudo()
        result = super().unlink()
        # a rule on payslips stays for their history, archived
        used = self.env['hr.payslip.line'].sudo().search([('salary_rule_id', 'in', rules.ids)]).salary_rule_id
        used.active = False
        (rules - used).unlink()
        return result

    def action_open_rule(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.salary.rule',
            'res_id': self.rule_id.id,
            'view_mode': 'form',
        }

    def _rule_values(self):
        self.ensure_one()
        sign = '-' if self.kind == 'deduction' else ''
        return {
            'name': self.name,
            'code': self.code,
            'sequence': 67 if self.kind == 'deduction' else 57,
            'category_id': self.category_id.id,
            'condition_select': 'python',
            'condition_python': 'result = bool(inputs.%s.amount)' % self.code,
            'amount_select': 'code',
            'amount_python_compute': '# the payroll adjustments due, filled in when the payslip is computed\n'
                                     'result = %sinputs.%s.amount' % (sign, self.code),
            'active': self.active,
            'company_id': self.company_id.id,
            'note': _('Pays the payroll adjustments of type %s. Kept in sync by the adjustment type.', self.name),
        }

    def _sync_rule(self, old_structures=None):
        """ The salary rule of the type, its input, and its place in the structures of the type. """
        Rule = self.env['hr.salary.rule'].sudo()
        for adjustment_type in self:
            values = adjustment_type._rule_values()
            rule = adjustment_type.rule_id.sudo()
            if rule:
                rule.write(values)
                rule.input_ids.write({'name': adjustment_type.name, 'code': adjustment_type.code})
            else:
                rule = Rule.create(dict(values, input_ids=[(0, 0, {
                    'name': adjustment_type.name, 'code': adjustment_type.code})]))
                super(OmHrPayrollAdjustmentType, adjustment_type).write({'rule_id': rule.id})
            previous = (old_structures or {}).get(adjustment_type, self.env['hr.payroll.structure'])
            for structure in (previous - adjustment_type.structure_ids).sudo():
                structure.rule_ids = [(3, rule.id)]
            for structure in adjustment_type.structure_ids.sudo():
                if rule not in structure.rule_ids:
                    structure.rule_ids = [(4, rule.id)]
