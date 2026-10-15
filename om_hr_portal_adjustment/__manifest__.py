{
    'name': 'HR Portal: Pay Adjustments',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employees follow the bonuses, commissions and deductions of their pay on the website portal',
    'description': 'Adds a Pay Adjustments page to My HR on the website portal: the employees see their running and '
                   'done pay adjustments, with the amount, the recurrence and each monthly line. Installs by itself '
                   'with HR Portal and Payroll Adjustments. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_portal', 'om_hr_payroll_adjustment'],
    'data': ['views/portal_templates.xml'],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
