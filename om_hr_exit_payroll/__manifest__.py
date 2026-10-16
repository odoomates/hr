{
    'name': 'HR Exit in Payroll',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Final settlement payslip of an exit: last salary, leave encashment, gratuity, loans still due',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_exit', 'om_hr_payroll'],
    'data': [
        'data/hr_salary_rule_data.xml',
        'views/om_hr_exit_views.xml',
        'views/hr_work_entry_type_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
