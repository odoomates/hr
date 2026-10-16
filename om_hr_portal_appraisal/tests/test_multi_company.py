from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalMultiCompanyCase


@tagged('post_install', '-at_install')
class TestPortalAppraisalMultiCompany(HrPortalMultiCompanyCase):

    def test_appraisals_of_the_other_company(self):
        appraisal_a = self.env['hr.appraisal'].create({'employee_id': self.employee.id})
        appraisal_a.action_start()
        goal_a = self.env['hr.appraisal.goal'].create({'name': 'Goal of Company A', 'employee_id': self.employee.id})
        self.login_employee_b()
        self.assertEqual(self.get('/my/hr/appraisals/%s' % appraisal_a.id).status_code, 404)
        self.assertNotIn('Goal of Company A', self.get('/my/hr/appraisals').text)
        response = self.url_open('/my/hr/goals/%s/progress' % goal_a.id,
                                 data={'csrf_token': self.csrf_token(), 'progress': '50'})
        self.assertEqual(response.status_code, 404)
