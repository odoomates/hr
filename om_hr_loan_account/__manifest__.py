{
    'name': 'HR Loans in Accounting',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Pay employee loans out, and take their repayments, as payments on a receivable loan account',
    'description': 'A loan type gets a loan account and a payment journal. A loan paid out is an outgoing payment '
                   'to the employee on the loan account; an installment repaid outside the payroll, or a loan '
                   'settled at once, is an incoming payment. The loan account is reconciled per employee. '
                   'Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_loan', 'account'],
    'data': [
        'views/om_hr_loan_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
