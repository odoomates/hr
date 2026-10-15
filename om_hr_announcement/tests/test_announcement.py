from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestAnnouncement(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hr_user = new_test_user(cls.env, 'om_ann_hr', groups='base.group_user,hr.group_hr_user')
        cls.manager_user = new_test_user(cls.env, 'om_ann_manager', groups='base.group_user')
        cls.user_a = new_test_user(cls.env, 'om_ann_a', groups='base.group_user')
        cls.user_b = new_test_user(cls.env, 'om_ann_b', groups='base.group_user')
        Employee = cls.env['hr.employee']
        cls.manager = Employee.create({'name': 'Ann Manager', 'user_id': cls.manager_user.id})
        cls.sales = cls.env['hr.department'].create({'name': 'Ann Sales', 'manager_id': cls.manager.id})
        cls.sales_east = cls.env['hr.department'].create({'name': 'Ann Sales East', 'parent_id': cls.sales.id})
        cls.other = cls.env['hr.department'].create({'name': 'Ann Other'})
        cls.employee_a = Employee.create({'name': 'Ann A', 'user_id': cls.user_a.id,
                                          'department_id': cls.sales_east.id})
        cls.employee_b = Employee.create({'name': 'Ann B', 'user_id': cls.user_b.id, 'department_id': cls.other.id})
        cls.Announcement = cls.env['om.hr.announcement'].with_user(cls.hr_user)

    def announcement(self, **values):
        return self.Announcement.create({'name': 'Office closed Friday', 'body': '<p>Enjoy the long weekend.</p>',
                                         **values})

    def visible(self, user):
        return self.env['om.hr.announcement'].with_user(user).search([])

    def test_audience(self):
        everyone = self.announcement()
        self.assertGreaterEqual(everyone.audience_count, 3)
        sales = self.announcement(audience='department', department_ids=[Command.set(self.sales.ids)])
        self.assertEqual(sales._om_audience(), self.employee_a, 'sub-departments included')
        tag = self.env['hr.employee.category'].create({'name': 'Ann Night Team'})
        self.employee_b.category_ids = tag
        tagged_ = self.announcement(audience='tag', category_ids=[Command.set(tag.ids)])
        self.assertEqual(tagged_._om_audience(), self.employee_b)

    def test_publish_read_acknowledge(self):
        announcement = self.announcement(audience='employee', requires_ack=True,
                                         employee_ids=[Command.set((self.employee_a | self.employee_b).ids)])
        announcement.action_publish()
        self.assertEqual((announcement.state, announcement.recipient_count), ('published', 2))
        self.assertIn(announcement, self.visible(self.user_a))
        mine = announcement.with_user(self.user_a)
        self.assertEqual(mine.my_state, 'unread')
        self.assertEqual(self.env['om.hr.announcement'].with_user(self.user_a).om_systray_data()['count'], 1)
        mine.web_read({'name': {}, 'body': {}})
        mine.invalidate_recordset(['my_state'])
        self.assertEqual(mine.my_state, 'read', 'opening it marks it read')
        self.assertEqual(self.env['om.hr.announcement'].with_user(self.user_a).om_systray_data()['count'], 1,
                         'still to acknowledge')
        mine.action_acknowledge()
        mine.invalidate_recordset(['my_state'])
        self.assertEqual(mine.my_state, 'acknowledged')
        self.assertEqual(self.env['om.hr.announcement'].with_user(self.user_a).om_systray_data()['count'], 0)
        announcement.invalidate_recordset()
        self.assertEqual((announcement.read_rate, announcement.ack_rate), (50.0, 50.0))
        self.assertEqual(self.env['om.hr.announcement'].with_user(self.user_a).search(
            [('my_state', '=', 'acknowledged')]), announcement)

    def test_only_addressed_and_published(self):
        draft = self.announcement()
        sales = self.announcement(audience='department', department_ids=[Command.set(self.sales.ids)])
        sales.action_publish()
        self.assertNotIn(draft, self.visible(self.user_a), 'a draft stays with its author')
        self.assertIn(sales, self.visible(self.user_a))
        self.assertNotIn(sales, self.visible(self.user_b), 'not addressed to B')
        with self.assertRaises(AccessError):
            sales.with_user(self.user_b).read(['body'])
        with self.assertRaises(UserError):
            sales.with_user(self.user_b).action_acknowledge()

    def test_department_manager_publishes_to_own_departments(self):
        Manager = self.env['om.hr.announcement'].with_user(self.manager_user)
        mine = Manager.create({'name': 'Team lunch', 'audience': 'department',
                               'department_ids': [Command.set(self.sales_east.ids)]})
        mine.action_publish()
        self.assertEqual(mine.recipient_ids.employee_id, self.employee_a)
        with self.assertRaises(ValidationError):
            Manager.create({'name': 'To all', 'audience': 'company'})
        with self.assertRaises(ValidationError):
            Manager.create({'name': 'Other team', 'audience': 'department',
                            'department_ids': [Command.set(self.other.ids)]})
        with self.assertRaises(ValidationError):
            self.env['om.hr.announcement'].with_user(self.user_a).create({'name': 'Me', 'audience': 'company'})

    def test_scheduled_expired_and_reminded(self):
        now = fields.Datetime.now()
        later = self.announcement(date_start=now + timedelta(days=2), requires_ack=True, remind_after_days=3,
                                  date_end=(now + timedelta(days=10)).date())
        later.action_publish()
        self.assertEqual(later.state, 'scheduled')
        Announcement = self.env['om.hr.announcement']
        with patch.object(fields.Datetime, 'now', lambda *a, **k: now + timedelta(days=2, hours=1)):
            Announcement._cron_om_announcements()
        self.assertEqual(later.state, 'published')
        self.assertFalse(later.date_reminded)
        with patch.object(fields.Datetime, 'now', lambda *a, **k: now + timedelta(days=6)):
            Announcement._cron_om_announcements()
        self.assertTrue(later.date_reminded, 'reminded once after 3 days')
        self.assertIn('reminded', later.message_ids[0].body)
        with patch.object(fields.Date, 'context_today', lambda *a, **k: (now + timedelta(days=11)).date()):
            Announcement._cron_om_announcements()
        self.assertEqual(later.state, 'expired')
        self.assertNotIn(later, self.env['om.hr.announcement'].with_user(self.user_a).search(
            [('state', '=', 'published')]))

    def test_recipients_notified(self):
        announcement = self.announcement(audience='employee', employee_ids=[Command.set(self.employee_a.ids)])
        announcement.action_publish()
        notified = self.env['mail.message'].search([('model', '=', 'om.hr.announcement'),
                                                    ('res_id', '=', announcement.id),
                                                    ('partner_ids', 'in', self.user_a.partner_id.ids)])
        self.assertTrue(notified)

    def test_nobody_reached(self):
        nobody = self.announcement(audience='job', job_ids=[Command.set(self.env['hr.job'].create(
            {'name': 'Ann Astronaut'}).ids)])
        with self.assertRaises(UserError):
            nobody.action_publish()


@tagged('post_install', '-at_install')
class TestAnnouncementSystray(HttpCase):

    def test_systray(self):
        user = new_test_user(self.env, 'om_ann_tour', groups='base.group_user', password='om_ann_tour')
        employee = self.env['hr.employee'].create({'name': 'Ann Tour', 'user_id': user.id})
        announcement = self.env['om.hr.announcement'].create({
            'name': 'Fire drill on Monday', 'body': '<p>Meet in the car park.</p>', 'requires_ack': True,
            'audience': 'employee', 'employee_ids': [Command.set(employee.ids)]})
        announcement.action_publish()
        self.start_tour('/odoo', 'om_hr_announcement_systray', login='om_ann_tour')
        self.assertTrue(announcement.recipient_ids.ack_date)
