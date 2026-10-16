from odoo import SUPERUSER_ID, api

from odoo.addons.om_hr_payroll.company_check import report_company_inconsistencies


def migrate(cr, version):
    """ The payroll accounting now checks the companies of its journals, accounts and taxes: report the records
        already linking another company. """
    report_company_inconsistencies(api.Environment(cr, SUPERUSER_ID, {}), 'om_hr_payroll_account')
