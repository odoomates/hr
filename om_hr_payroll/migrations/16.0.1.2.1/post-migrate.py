def migrate(cr, version):
    # the payslips and batches created without the flag stored NULL: they are no refunds
    cr.execute("UPDATE hr_payslip SET credit_note = FALSE WHERE credit_note IS NULL")
    cr.execute("UPDATE hr_payslip_run SET credit_note = FALSE WHERE credit_note IS NULL")
