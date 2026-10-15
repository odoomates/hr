import logging

_logger = logging.getLogger(__name__)

# The external ids om_hr_payroll used to own and om_hr_base owns now
FROM_PAYROLL = (
    'field_hr_employee__type_id',
    'field_hr_version__type_id',
    'menu_contract_type',
)


def take_over(cr, names=FROM_PAYROLL, source='om_hr_payroll'):
    """ Give om_hr_base the external ids of the records it now declares in place of `source`.

    It runs before om_hr_base loads its data, from the install hook of om_hr_base and from the upgrade
    script of om_hr_payroll, so that om_hr_base takes over the records instead of creating them again,
    and the upgrade of `source` does not delete them. The records keep their database id. Running it
    again changes nothing.

    :return: the names of the external ids taken over
    """
    cr.execute("""
        UPDATE ir_model_data imd
           SET module = 'om_hr_base'
         WHERE imd.module = %s
           AND imd.name IN %s
           AND NOT EXISTS (SELECT 1 FROM ir_model_data base
                            WHERE base.module = 'om_hr_base' AND base.name = imd.name)
     RETURNING imd.name
    """, [source, tuple(names)])
    taken = sorted(row[0] for row in cr.fetchall())
    if taken:
        _logger.info('om_hr_base: took over %s record(s) of %s: %s', len(taken), source, ', '.join(taken))
    return taken
