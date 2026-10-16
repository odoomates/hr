from odoo import SUPERUSER_ID, api

from odoo.addons.om_hr_payroll.company_check import report_company_inconsistencies


def migrate(cr, version):
    """ The payroll now checks the companies of its links: the payslip lines take the company of their payslip,
        then the records already linking another company are reported. """
    cr.execute("""
        UPDATE hr_payslip_line line
           SET company_id = slip.company_id
          FROM hr_payslip slip
         WHERE line.slip_id = slip.id AND line.company_id IS DISTINCT FROM slip.company_id
    """)
    report_company_inconsistencies(api.Environment(cr, SUPERUSER_ID, {}), 'om_hr_payroll')
