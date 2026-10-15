{
    'name': 'HR Loans in Payroll Accounting',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'The loan installments deducted from the payslips repay the loan account of the employee',
    'description': 'The Loan Installments rule credits the loan account of the loan types, with the employee as '
                   'partner of the journal item, and the loan account is reconciled per employee once the payslips '
                   'are posted. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_loan_account', 'om_hr_loan_payroll', 'om_hr_payroll_account'],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
