{
    'name': 'Payroll Bank Files: Payments',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Register the salary payments in Accounting when exporting the bank file of the payslips',
    'description': 'An option of the bank file export registers the salary payments of its payslips in '
                   'Accounting, as Pay Salaries does, with the bank journal and the payment date you choose. '
                   'Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_payroll_export', 'om_hr_payroll_account'],
    'data': [
        'views/om_hr_payroll_export_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
