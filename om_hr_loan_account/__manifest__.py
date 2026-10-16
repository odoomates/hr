{
    'name': 'HR Loans in Accounting',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Pay employee loans out, and take their repayments, as payments on a receivable loan account',
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
