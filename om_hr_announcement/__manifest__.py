{
    'name': 'HR Announcements',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Company, department and job position announcements, read and acknowledged by the employees',
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
    'demo': ['demo/om_hr_announcement_demo.xml'],
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
