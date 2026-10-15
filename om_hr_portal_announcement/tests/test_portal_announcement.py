from odoo import Command
from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import OmHrPortalCase


@tagged('post_install', '-at_install')
class TestPortalAnnouncement(OmHrPortalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Announcement = cls.env['om.hr.announcement'].with_user(cls.hr_user)
        cls.mine = Announcement.create({
            'name': 'New leave policy', 'body': '<p>Read the new policy.</p>', 'requires_ack': True,
            'pinned': True, 'audience': 'employee', 'employee_ids': [Command.set(cls.employee.ids)]})
        cls.theirs = Announcement.create({
            'name': 'Colleague only', 'body': '<p>Not for you.</p>', 'audience': 'employee',
            'employee_ids': [Command.set(cls.colleague.ids)]})
        (cls.mine | cls.theirs).action_publish()

    def test_read_and_acknowledge(self):
        self.login_employee()
        page = self.get('/my/hr/announcements').text
        self.assertIn('New leave policy', page)
        self.assertNotIn('Colleague only', page)
        self.assertIn('/my/hr/announcements', self.get('/my/hr').text)
        detail = self.get('/my/hr/announcements/%s' % self.mine.id).text
        self.assertIn('Read the new policy.', detail)
        line = self.mine.recipient_ids
        self.assertTrue(line.read_date, 'opening it marks it read')
        self.url_open('/my/hr/announcements/%s/acknowledge' % self.mine.id, data={'csrf_token': self.csrf_token()})
        self.assertTrue(line.ack_date)

    def test_no_one_else_s_announcement(self):
        self.login_employee()
        self.assertEqual(self.get('/my/hr/announcements/%s' % self.theirs.id).status_code, 404)
        response = self.url_open('/my/hr/announcements/%s/acknowledge' % self.theirs.id,
                                 data={'csrf_token': self.csrf_token()})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.theirs.recipient_ids.ack_date)
