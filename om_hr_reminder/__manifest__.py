{
    'name': 'HR Reminders',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Birthday, work anniversary and probation end reminders for employees, and the celebrations '
               'of the month',
    'description': 'The next birthday, work anniversary and probation end of each employee, kept up to date every '
                   'day, and ready-made Automation Rules giving the manager, or HR, a to-do on them. Every '
                   'employee sees the coming birthdays and work anniversaries of the month in My HR > '
                   'Celebrations. '
                   'Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_base', 'base_automation'],
    'data': [
        'data/om_hr_reminder_data.xml',
        'views/hr_employee_views.xml',
    ],
    'images': ['static/description/banner.gif'],
}
