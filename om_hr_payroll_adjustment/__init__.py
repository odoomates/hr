from . import models
from . import wizard


def uninstall_hook(env):
    """ The salary rules of the adjustment types go with the module, archived when payslips show them. """
    env['om.hr.payroll.adjustment.type'].with_context(active_test=False).search([]).unlink()
