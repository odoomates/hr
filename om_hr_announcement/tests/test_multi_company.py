from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestMultiCompany(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Announcements Company B'})
        cls.hr_a = new_test_user(cls.env, 'om_mc_ann_hr_a', groups='base.group_user,hr.group_hr_user',
                                 company_id=cls.company_a.id, company_ids=[Command.set(cls.company_a.ids)])
        Employee = cls.env['hr.employee']
        cls.employee_a = Employee.create({'name': 'Reader A', 'company_id': cls.company_a.id})
        cls.employee_b = Employee.create({'name': 'Reader B', 'company_id': cls.company_b.id})
        Announcement = cls.env['hr.announcement']
        cls.announcement_a = Announcement.create({'name': 'News of A', 'company_id': cls.company_a.id})
        cls.announcement_b = Announcement.create({'name': 'News of B', 'company_id': cls.company_b.id})

    def test_announcements(self):
        Announcement = self.env['hr.announcement'].with_user(self.hr_a)
        self.assertEqual(Announcement.search([('id', 'in', (self.announcement_a | self.announcement_b).ids)]),
                         self.announcement_a)
        with self.assertRaises(AccessError):
            self.announcement_b.with_user(self.hr_a).read(['name'])

    def test_recipients(self):
        Read = self.env['hr.announcement.read']
        with self.assertRaises(UserError):
            Read.create({'announcement_id': self.announcement_a.id, 'employee_id': self.employee_b.id})
        line = Read.create({'announcement_id': self.announcement_b.id, 'employee_id': self.employee_b.id})
        self.assertEqual(line.company_id, self.company_b)
        self.assertFalse(Read.with_user(self.hr_a).search([('id', '=', line.id)]))
