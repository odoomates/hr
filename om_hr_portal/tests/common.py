from datetime import date

from odoo.tests import HttpCase, new_test_user


class HrPortalCase(HttpCase):
    """ An employee with a portal user, and a colleague with one too, for the HR pages of the website. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hr_user = new_test_user(cls.env, 'om_portal_hr', groups='base.group_user,hr.group_hr_manager')
        cls.manager_user = new_test_user(cls.env, 'om_portal_manager', groups='base.group_user')
        Employee = cls.env['hr.employee']
        cls.manager = Employee.create({'name': 'Portal Manager', 'user_id': cls.manager_user.id})
        values = {'parent_id': cls.manager.id, 'date_version': date(2025, 1, 1),
                  'contract_date_start': date(2025, 1, 1), 'wage': 3000.0}
        cls.employee = Employee.create({'name': 'Portal Employee', 'work_email': 'portal.employee@example.com',
                                        'job_title': 'Storekeeper', **values})
        cls.colleague = Employee.create({'name': 'Portal Colleague', 'work_email': 'portal.colleague@example.com',
                                         **values})
        cls.employee.with_user(cls.hr_user).action_grant_portal()
        cls.colleague.with_user(cls.hr_user).action_grant_portal()
        cls.portal_user = cls.employee.user_id
        cls.colleague_user = cls.colleague.user_id
        for user in (cls.portal_user, cls.colleague_user):
            user.password = user.login

    def login_employee(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)

    def get(self, url):
        return self.url_open(url, allow_redirects=False)
