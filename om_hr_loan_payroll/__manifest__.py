{
    'name': 'HR Loans in Payroll',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Deduct the employee loan installments from the payslips, and mark them repaid with the payslip',
    'description': 'Adds the Loan Installments salary rule (code LOAN, a deduction). Computing a payslip gives it '
                   'the installments due by the end of its period and not deducted yet, those of earlier months '
                   'included. Confirming the payslip marks them repaid; cancelling or refunding it makes them due '
                   'again. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_loan', 'om_hr_payroll'],
    'data': [
        'data/hr_salary_rule_data.xml',
        'views/om_hr_loan_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
