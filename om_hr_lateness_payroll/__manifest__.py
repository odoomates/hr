{
    'name': 'HR Lateness Payroll',
    'version': '20.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'The lateness penalties of a month taken off the payslips, as payroll adjustments',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_payroll', 'om_hr_lateness', 'om_hr_payroll_adjustment'],
    'data': [
        'security/ir.access.csv',
        'data/om_hr_lateness_payroll_data.xml',
        'views/om_hr_lateness_payroll_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
