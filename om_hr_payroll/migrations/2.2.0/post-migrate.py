import logging

from odoo.addons.om_hr_base.moved import FROM_PAYROLL

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """ Upgrade to 2.2.0: warn about the moved records om_hr_base did not take over. """
    if not version:
        return
    cr.execute("""
        SELECT name
          FROM ir_model_data
         WHERE module = 'om_hr_payroll' AND name IN %s
    """, [FROM_PAYROLL])
    left = [row[0] for row in cr.fetchall()]
    if left:
        _logger.warning('om_hr_payroll: upgrade to 2.2.0, records not taken over by om_hr_base: %s', ', '.join(left))
    # the worked days of the companies upgraded stay computed from the working schedule, as before
    cr.execute("UPDATE res_company SET om_payroll_worked_days_source = 'schedule'")
