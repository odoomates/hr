from odoo import api, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    @api.model
    def _hr_overtime_add_to_base_structure(self):
        """ The structures created from now on pay the overtime: the base structure gets the rule. The structures
            of the user are left as they are. """
        structure = self.env.ref('om_hr_payroll.structure_base', raise_if_not_found=False)
        rule = self.env.ref('om_hr_overtime_payroll.hr_rule_overtime', raise_if_not_found=False)
        if structure and rule and rule not in structure.rule_ids:
            structure.rule_ids = [(4, rule.id)]
