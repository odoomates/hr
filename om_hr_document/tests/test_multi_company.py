from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestDocumentMultiCompany(TransactionCase):
    """ A document stays in the company of its employee, of a type of that company or a shared one. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Document Company B'})
        cls.hr_user = new_test_user(cls.env, 'om_document_mc_hr', groups='base.group_user,hr.group_hr_user',
                                    company_id=cls.company_a.id, company_ids=[Command.set(cls.company_a.ids)])
        Employee = cls.env['hr.employee']
        cls.employee_a = Employee.create({'name': 'Holder A'})
        cls.employee_b = Employee.with_company(cls.company_b).create({'name': 'Holder B',
                                                                       'company_id': cls.company_b.id})
        cls.type_b = cls.env['document.type'].create({
            'name': 'Permit B', 'model_id': cls.env['ir.model']._get_id('hr.employee'),
            'company_id': cls.company_b.id})
        cls.passport = cls.env.ref('om_hr_document.document_type_passport')

    def document(self, employee, document_type):
        return self.env['document.document'].create({'res_model': 'hr.employee', 'res_id': employee.id,
                                                     'type_id': document_type.id})

    def test_other_company_hidden(self):
        document_a, document_b = self.document(self.employee_a, self.passport), \
            self.document(self.employee_b, self.passport)
        self.assertEqual((document_a.company_id, document_b.company_id), (self.company_a, self.company_b))
        Document = self.env['document.document'].with_user(self.hr_user)
        self.assertEqual(Document.search([('id', 'in', (document_a | document_b).ids)]), document_a)
        with self.assertRaises(AccessError):
            document_b.with_user(self.hr_user).read(['name'])

    def test_no_link_across_companies(self):
        with self.assertRaises(UserError):
            self.document(self.employee_a, self.type_b)

    def test_shared_type(self):
        self.assertFalse(self.passport.company_id)
        self.assertTrue(self.document(self.employee_a, self.passport))
        self.assertTrue(self.document(self.employee_b, self.passport))
