{
    'name': 'HR Reminders',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Birthday, work anniversary and probation end reminders for employees, and the celebrations '
               'of the month',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_base', 'base_automation'],
    'data': [
        'data/om_hr_reminder_data.xml',
        'views/hr_employee_views.xml',
    ],
    'demo': ['demo/om_hr_reminder_demo.xml'],
    'images': ['static/description/banner.gif'],
}
