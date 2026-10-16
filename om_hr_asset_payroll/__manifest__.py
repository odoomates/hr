{
    'name': 'HR Assets in Payroll',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Deduct from the payslip what an employee is charged for an asset lost or damaged',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_asset', 'om_hr_payroll'],
    'data': [
        'data/hr_salary_rule_data.xml',
        'views/om_hr_asset_assignment_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
