from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalMultiCompanyCase


@tagged('post_install', '-at_install')
class TestPortalSignMultiCompany(HrPortalMultiCompanyCase):

    def test_policies_of_the_company(self):
        Policy = self.env['hr.policy'].with_user(self.hr_user)
        Version = self.env['hr.policy.version']
        policy_a = Policy.create({'name': 'Rules of Company A', 'company_id': self.company_a.id})
        policy_b = Policy.create({'name': 'Rules of Company B', 'company_id': self.company_b.id})
        versions = Version.create([{'policy_id': policy_a.id, 'body': '<p>A</p>'},
                                   {'policy_id': policy_b.id, 'body': '<p>B</p>'}])
        versions.with_user(self.hr_user).action_publish()
        assignment_a = versions[0].assignment_ids.filtered(lambda a: a.employee_id == self.employee)
        self.assertFalse(versions[0].assignment_ids.filtered(lambda a: a.employee_id == self.employee_b))
        self.login_employee_b()
        page = self.get('/my/hr/policies').text
        self.assertIn('Rules of Company B', page)
        self.assertNotIn('Rules of Company A', page)
        self.assertEqual(self.get('/my/hr/policies/%s' % assignment_a.id).status_code, 404)
