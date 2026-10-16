
from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalCase


@tagged('post_install', '-at_install')
class TestPortalAppraisal(HrPortalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Appraisal = cls.env['hr.appraisal']
        cls.appraisal = Appraisal.create({'employee_id': cls.employee.id})
        cls.appraisal.action_start()
        cls.theirs = Appraisal.create({'employee_id': cls.colleague.id})
        Goal = cls.env['hr.appraisal.goal']
        cls.goal = Goal.create({'name': 'Portal Goal', 'employee_id': cls.employee.id})
        cls.their_goal = Goal.create({'name': 'Their Goal', 'employee_id': cls.colleague.id})

    def test_self_assessment(self):
        self.login_employee()
        url = '/my/hr/appraisals/%s' % self.appraisal.id
        self.assertIn('My work', self.get(url).text, 'the questions of the template')
        self.url_open(url + '/save', data={'csrf_token': self.csrf_token(), 'feedback': 'I closed the books.'})
        self.assertIn('closed the books', self.appraisal.sudo().employee_feedback_html)
        self.assertEqual(self.appraisal.state, 'self')
        self.appraisal.sudo().manager_feedback_html = '<p>Private review notes</p>'
        self.url_open(url + '/save', data={'csrf_token': self.csrf_token(), 'feedback': 'Final.', 'submit': '1'})
        self.assertEqual(self.appraisal.state, 'review')
        self.assertNotIn('Private review notes', self.get(url).text, 'the review shows once done')
        self.assertEqual(self.url_open(url + '/save', data={'csrf_token': self.csrf_token(), 'feedback': 'Late'},
                                       allow_redirects=False).status_code, 404, 'no change once submitted')

    def test_goals_and_privacy(self):
        self.login_employee()
        self.url_open('/my/hr/goals/%s/progress' % self.goal.id,
                      data={'csrf_token': self.csrf_token(), 'progress': '70'})
        self.assertEqual(self.goal.progress, 70)
        self.assertEqual(self.url_open('/my/hr/goals/%s/progress' % self.their_goal.id,
                                       data={'csrf_token': self.csrf_token(), 'progress': '5'}).status_code, 404)
        self.assertEqual(self.get('/my/hr/appraisals/%s' % self.theirs.id).status_code, 404)
        self.assertNotIn('Their Goal', self.get('/my/hr/appraisals').text)
