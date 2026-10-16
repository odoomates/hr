{
    'name': 'Shift Allowances in Payroll',
    'version': '20.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Pay the allowance of each published shift on the payslips, e.g. a night shift allowance',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_shift', 'om_hr_payroll'],
    'data': [
        'data/hr_salary_rule_data.xml',
        'views/om_hr_shift_payroll_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
