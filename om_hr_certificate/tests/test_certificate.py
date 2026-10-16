from datetime import date

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestCertificate(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee_user = new_test_user(cls.env, 'om_cert_employee', groups='base.group_user')
        cls.other_user = new_test_user(cls.env, 'om_cert_other', groups='base.group_user')
        cls.manager_user = new_test_user(cls.env, 'om_cert_manager', groups='base.group_user')
        cls.hr_admin = new_test_user(cls.env, 'om_cert_hr_admin', groups='base.group_user,hr.group_hr_manager')
        cls.env.ref('om_hr_certificate.flow_om_hr_certificate_hr').group_id = cls.env['res.groups'].create({
            'name': 'Certificate Approvers', 'user_ids': [Command.link(cls.hr_admin.id)]})
        Employee = cls.env['hr.employee']
        cls.manager = Employee.create({'name': 'Cert Manager', 'user_id': cls.manager_user.id})
        cls.employee = Employee.create({
            'name': 'Cert Employee', 'user_id': cls.employee_user.id, 'parent_id': cls.manager.id,
            'job_title': 'Accountant', 'date_version': date(2024, 1, 1), 'contract_date_start': date(2024, 1, 1),
            'wage': 3000.0})
        cls.other = Employee.create({'name': 'Cert Other', 'user_id': cls.other_user.id})
        cls.salary = cls.env.ref('om_hr_certificate.template_salary_certificate')

    def request(self, template=None, **values):
        return self.env['hr.certificate'].with_user(self.employee_user).create({
            'employee_id': self.employee.id, 'template_id': (template or self.salary).id,
            'addressee': 'Emirates NBD', 'purpose': 'Bank account', **values})

    def approve(self, certificate):
        certificate.with_user(self.employee_user).action_submit()
        self.assertEqual((certificate.state, certificate.approval_step), ('to_approve', 'Manager'))
        certificate.with_user(self.manager_user).action_approval_approve()
        certificate.with_user(self.hr_admin).action_approval_approve()

    def test_request_approved_and_printed(self):
        certificate = self.request()
        self.approve(certificate)
        self.assertEqual(certificate.state, 'issued')
        issue = certificate.issue_id
        self.assertEqual((issue.state, issue.employee_id, issue.addressee), ('issued', self.employee, 'Emirates NBD'))
        self.assertTrue(issue.name.startswith('SAL/'))
        self.assertIn('Cert Employee', issue.body_html)
        self.assertIn('Accountant', issue.body_html)
        self.assertIn('3,000.00', issue.body_html, 'the wage is printed though the employee cannot read it')

        # the employee downloads it
        action = certificate.with_user(self.employee_user).action_download()
        self.assertIn(str(issue.attachment_id.id), action['url'])
        issue.attachment_id.with_user(self.employee_user).read(['name'])
        with self.assertRaises(AccessError):
            issue.with_user(self.other_user).read(['name'])
        with self.assertRaises(AccessError):
            certificate.with_user(self.other_user).read(['name'])

    def test_only_requestable_templates(self):
        self.salary.employee_request = False
        with self.assertRaises(UserError):
            self.request().with_user(self.employee_user).action_submit()

    def test_refused(self):
        certificate = self.request()
        certificate.with_user(self.employee_user).action_submit()
        certificate.with_user(self.manager_user).action_approval_refuse('Not now')
        self.assertEqual(certificate.state, 'refused')
        self.assertFalse(certificate.issue_id)

    def test_hr_manager_cancels(self):
        certificate = self.request()
        self.approve(certificate)
        with self.assertRaises(UserError):
            certificate.issue_id.with_user(self.employee_user).action_cancel()
        self.assertFalse(certificate.issue_id.with_user(self.employee_user).can_cancel)
        self.assertFalse(self.hr_admin.has_group('om_print_template.group_print_manager'))
        self.assertTrue(certificate.issue_id.with_user(self.hr_admin).can_cancel,
                        'the Cancel button shows for an HR manager, not only for the print administrators')
        certificate.issue_id.with_user(self.hr_admin).action_cancel()
        self.assertEqual(certificate.issue_id.state, 'cancelled')

    def test_print_menu_of_the_employee(self):
        bindings = self.env['ir.actions.actions'].get_bindings('hr.employee').get('report', [])
        self.assertIn(self.salary.ref_ir_act_window.id, [binding['id'] for binding in bindings])
        self.employee.invalidate_recordset()
        certificate = self.request()
        self.approve(certificate)
        self.employee.invalidate_recordset()
        self.assertEqual(self.employee.print_issue_count, 1)
