from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestMultiCompany(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Certificates Company B'})
        cls.hr_a = new_test_user(cls.env, 'om_mc_cert_hr_a', groups='base.group_user,hr.group_hr_user',
                                 company_id=cls.company_a.id, company_ids=[Command.set(cls.company_a.ids)])
        Employee = cls.env['hr.employee']
        cls.employee_a = Employee.create({'name': 'Certified A', 'company_id': cls.company_a.id})
        cls.employee_b = Employee.create({'name': 'Certified B', 'company_id': cls.company_b.id})
        cls.template_b = cls.env['print.template'].create({
            'name': 'Letter of B', 'model_id': cls.env['ir.model']._get_id('hr.employee'),
            'employee_request': True, 'company_id': cls.company_b.id, 'body_html': '<p>Hello</p>'})
        cls.shared = cls.env.ref('om_hr_certificate.template_employment_certificate')

    def test_requests(self):
        certificate_b = self.env['hr.certificate'].create({'employee_id': self.employee_b.id,
                                                           'template_id': self.template_b.id})
        self.assertEqual(certificate_b.company_id, self.company_b)
        self.assertFalse(self.env['hr.certificate'].with_user(self.hr_a).search([('id', '=', certificate_b.id)]))
        with self.assertRaises(AccessError):
            certificate_b.with_user(self.hr_a).read(['name'])

    def test_no_link_across_companies(self):
        with self.assertRaises(UserError):
            self.env['hr.certificate'].create({'employee_id': self.employee_a.id, 'template_id': self.template_b.id})
        self.assertTrue(self.env['hr.certificate'].create({'employee_id': self.employee_b.id,
                                                           'template_id': self.shared.id}),
                        'a template without company serves every company')
