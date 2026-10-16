{
    'name': 'Odoo 20 HR Payroll Accounting',
    'version': '1.2.3',
    'category': 'Generic Modules/Human Resources',
    'summary': 'Payroll accounting for Odoo 20 Community: payslip journal entries and salary payments',
    'description': 'Connects the payroll to Accounting. Each confirmed payslip posts a journal entry built from the '
                   'debit and credit accounts of its salary rules, or a payslip batch posts one consolidated '
                   'entry. The net salaries are paid from a payslip or a batch with Pay Salaries, and each payslip '
                   'shows its payment status. Part of Odoo Mates HR.',
    'author': 'Odoo Mates, Odoo SA',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': [
        'om_hr_payroll',
        'account'
    ],
    'data': [
        'security/ir.access.csv',
        'views/hr_payroll_account_views.xml',
        'wizard/hr_payslip_payment_register_views.xml',
    ],
    'demo': [
        'demo/hr_payroll_account_demo.xml',
    ],
    'images': ['static/description/banner.gif'],
    'sequence': 1,
    'live_test_url': 'https://www.youtube.com/watch?v=0kaHMTtn7oY',
    'application': True,
    'auto_install': True,
}
