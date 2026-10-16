from odoo import api, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    @api.model
    def _hr_asset_add_to_base_structure(self):
        """ The structures created from now on deduct the asset charges: the base structure gets the rule. The
            structures of the user are left as they are. """
        structure = self.env.ref('om_hr_payroll.structure_base', raise_if_not_found=False)
        rule = self.env.ref('om_hr_asset_payroll.hr_rule_asset', raise_if_not_found=False)
        if structure and rule and rule not in structure.rule_ids:
            structure.rule_ids = [(4, rule.id)]
