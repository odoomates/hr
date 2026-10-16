"""Report, on upgrade, the records of a module linking records of another company, without changing them."""
import logging

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def report_company_inconsistencies(env, module):
    """ Log the records whose fields of `module` checking the company link a record of another company: the
        next change of such a record is refused until the link is fixed. """
    found = 0
    for model_name in env.registry:
        Model = env[model_name]
        if Model._abstract or Model._transient or not Model._auto:
            continue
        fnames = [name for name, field in Model._fields.items()
                  if field.relational and field.check_company and field.store
                  and module in (field._modules or ())]
        if not fnames:
            continue
        for record in Model.with_context(active_test=False).search([]):
            try:
                record._check_company(fnames)
            except UserError as error:
                found += 1
                _logger.warning('%s: %s %s links a record of another company, fix it before changing it: %s',
                                module, Model._description, record.display_name, error)
    if found:
        _logger.warning('%s: %s records link records of another company, see above.', module, found)
