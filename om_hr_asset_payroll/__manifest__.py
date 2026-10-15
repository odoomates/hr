{
    'name': 'HR Assets in Payroll',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Deduct from the payslip what an employee is charged for an asset lost or damaged',
    'description': 'The charge set when an asset is returned damaged or reported lost is deducted by the Asset '
                   'Charges salary rule from the next payslip of the employee, or from their final settlement. '
                   'Each charge is deducted once, and again only if its payslip is cancelled or refunded. '
                   'Part of Odoo Mates HR.',
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
