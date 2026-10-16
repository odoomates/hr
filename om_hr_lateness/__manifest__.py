{
    'name': 'HR Lateness',
    'version': '20.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Late arrivals and early departures against the working schedule: grace minutes, penalty matrix, '
               'warnings, excuses',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['hr_attendance', 'om_hr_base'],
    'data': [
        'security/ir.access.csv',
        'data/om_hr_lateness_data.xml',
        'views/om_hr_lateness_views.xml',
    ],
    'images': ['static/description/banner.gif'],
}
