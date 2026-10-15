{
    'name': 'Shift Allowances in Payroll',
    'version': '1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Pay the allowance of each published shift on the payslips, e.g. a night shift allowance',
    'description': 'The allowance set on the shift templates is paid on the payslip for each published shift, '
                   'once, by the Shift Allowances salary rule. The shifts on time off or a public holiday are left '
                   'out, and the shifts published late are paid on the next payslip. '
                   'Part of Odoo Mates HR.',
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
