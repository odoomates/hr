from datetime import date

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestAppraisalMultiCompany(TransactionCase):
    """ An appraisal stays in the company of its employee, in a cycle of that company, with a feedback template
    of that company or a shared one. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Appraisal Company B'})
        cls.hr_user = new_test_user(cls.env, 'om_appraisal_mc_hr', groups='base.group_user,hr.group_hr_user',
                                    company_id=cls.company_a.id, company_ids=[Command.set(cls.company_a.ids)])
        Employee = cls.env['hr.employee']
        cls.employee_a = Employee.create({'name': 'Appraised A'})
        cls.employee_b = Employee.with_company(cls.company_b).create({'name': 'Appraised B',
                                                                       'company_id': cls.company_b.id})
        cls.cycle_b = cls.env['hr.appraisal.cycle'].with_company(cls.company_b).create({
            'name': 'Cycle B', 'date_start': date(2026, 1, 1), 'date_end': date(2026, 12, 31),
            'date_deadline': date(2026, 12, 15), 'company_id': cls.company_b.id})
        Template = cls.env['hr.appraisal.template']
        cls.template_b = Template.create({'name': 'Template B', 'company_id': cls.company_b.id})
        cls.shared_template = Template.create({'name': 'Shared Template'})

    def appraisal(self, employee, **values):
        return self.env['hr.appraisal'].create({'employee_id': employee.id, 'date_deadline': date(2026, 12, 1),
                                                **values})

    def test_other_company_hidden(self):
        appraisal_a, appraisal_b = self.appraisal(self.employee_a), self.appraisal(self.employee_b)
        Appraisal = self.env['hr.appraisal'].with_user(self.hr_user)
        self.assertEqual(Appraisal.search([('id', 'in', (appraisal_a | appraisal_b).ids)]), appraisal_a)
        with self.assertRaises(AccessError):
            appraisal_b.with_user(self.hr_user).read(['state'])

    def test_no_link_across_companies(self):
        with self.assertRaises(UserError):
            self.appraisal(self.employee_a, cycle_id=self.cycle_b.id)
        with self.assertRaises(UserError):
            self.appraisal(self.employee_a, template_id=self.template_b.id)

    def test_shared_template(self):
        self.assertTrue(self.appraisal(self.employee_a, template_id=self.shared_template.id))
        self.assertTrue(self.appraisal(self.employee_b, template_id=self.shared_template.id))
        templates = self.env['hr.appraisal.template'].with_user(self.hr_user).search([])
        self.assertIn(self.shared_template, templates)
        self.assertNotIn(self.template_b, templates, 'the templates of another company are not shown')
