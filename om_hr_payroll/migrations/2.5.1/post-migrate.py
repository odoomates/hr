def migrate(cr, version):
    """ The payslips and batches created without a credit note flag stored NULL: they are no refunds. The refunds
        made before link the payslip they take back: the one confirmed payslip of their employee and period. """
    cr.execute("UPDATE hr_payslip SET credit_note = FALSE WHERE credit_note IS NULL")
    cr.execute("UPDATE hr_payslip_run SET credit_note = FALSE WHERE credit_note IS NULL")
    cr.execute("""
        UPDATE hr_payslip refund
           SET refunded_id = original.id
          FROM hr_payslip original
         WHERE refund.credit_note AND refund.refunded_id IS NULL
           AND NOT original.credit_note AND original.state = 'done' AND original.id < refund.id
           AND (original.employee_id, original.date_from, original.date_to, original.company_id)
             = (refund.employee_id, refund.date_from, refund.date_to, refund.company_id)
           AND NOT EXISTS (
                SELECT 1
                  FROM hr_payslip other
                 WHERE other.id != original.id AND NOT other.credit_note AND other.state = 'done'
                   AND other.id < refund.id
                   AND (other.employee_id, other.date_from, other.date_to, other.company_id)
                     = (refund.employee_id, refund.date_from, refund.date_to, refund.company_id))
    """)
