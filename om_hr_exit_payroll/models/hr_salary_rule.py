from odoo import api, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    @api.model
    def _om_hr_exit_add_to_base_structure(self):
        """ The structures created from now on pay the final settlements. The structures of the user are left
            as they are. """
        structure = self.env.ref('om_hr_payroll.structure_base', raise_if_not_found=False)
        rules = self.env.ref('om_hr_exit_payroll.hr_rule_leave_encashment', raise_if_not_found=False) \
            | self.env.ref('om_hr_exit_payroll.hr_rule_gratuity', raise_if_not_found=False)
        if structure and rules:
            structure.rule_ids = [(4, rule.id) for rule in rules if rule not in structure.rule_ids]
