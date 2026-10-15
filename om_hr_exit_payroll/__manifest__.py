{
    'name': 'HR Exit in Payroll',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Final settlement payslip of an exit: last salary, leave encashment, gratuity, loans still due',
    'description': 'Creates the final settlement payslip of an exit, up to the last working day, with the unused '
                   'time off paid out, the end of service gratuity when HR Gratuity is installed, and the loan '
                   'installments still due deducted when HR Loans in Payroll is installed. The last salary is '
                   'prorated by the Partial Period rule of the payroll: add it to the salary structure, '
                   'otherwise the whole wage of the last month is paid. Part of Odoo Mates HR.',
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
