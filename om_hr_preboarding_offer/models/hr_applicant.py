from odoo import models
from odoo.exceptions import UserError


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    def create_employee_from_applicant(self):
        """ The new employee of an accepted offer starts their pre-boarding, when the company does so. """
        action = super().create_employee_from_applicant()
        offer = self._accepted_offer()
        employee = self.employee_id
        if offer and employee and employee.company_id.preboarding_from_offer:
            try:
                with self.env.cr.savepoint():
                    self.env['hr.preboarding']._start(employee, date_start=offer.date_start)
            except UserError as error:
                # the employee is created all the same; HR starts the pre-boarding once the problem is solved
                employee.message_post(body=self.env._('The pre-boarding could not start: %s', error),
                                      subtype_xmlid='mail.mt_note')
        return action
