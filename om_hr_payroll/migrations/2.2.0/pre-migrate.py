from odoo.addons.om_hr_base.moved import take_over


def migrate(cr, version):
    """ Upgrade to 2.2.0: the employee category of the contract and the Employee Types menu move to om_hr_base.

    om_hr_base, a new dependency, is installed before this script and takes the records over from its install
    hook. Taking them over here again covers the databases where om_hr_base was installed some other way.
    """
    if not version:
        return
    take_over(cr)
