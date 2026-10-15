{
    'name': 'Overtime in Payroll',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Pay the validated overtime of the Attendances app on the payslips, at the rate of each time rule',
    'description': 'The overtime the time rules of the Attendances app create, once validated, is paid on the '
                   'payslip: hours x hourly wage x the salary rate of the rule, e.g. 150% on weekdays and 200% on '
                   'public holidays. Each hour is paid once, and overtime validated late is paid on the next '
                   'payslip. '
                   'Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_payroll', 'hr_attendance'],
    'data': [
        'data/hr_salary_rule_data.xml',
        'views/hr_payslip_views.xml',
        'views/hr_attendance_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
