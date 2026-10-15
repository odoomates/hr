{
    'name': 'HR Announcements',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Company, department and job position announcements, read and acknowledged by the employees',
    'description': 'Announcements to the whole company, to departments, job positions, employee tags or chosen '
                   'employees, published now or on a date and shown until another. Each employee gets it in their '
                   'inbox or by email, reads it in My HR or from the megaphone of the top bar, and acknowledges it '
                   'when asked; the authors follow who read and acknowledged it, and remind the others. HR '
                   'publishes to anyone, a department manager to the departments they manage. '
                   'Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_base', 'mail'],
    'data': [
        'security/ir.access.csv',
        'data/om_hr_announcement_data.xml',
        'views/om_hr_announcement_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'om_hr_announcement/static/src/**/*',
        ],
        'web.assets_tests': [
            'om_hr_announcement/static/tests/tours/**/*',
        ],
    },
    'images': ['static/description/banner.gif'],
}
