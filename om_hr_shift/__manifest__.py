{
    'name': 'Shifts',
    'version': '20.0.1.0.0',
    'category': 'Human Resources/Shifts',
    'summary': 'Shift planning and rosters: shift templates, roster board, rotations, open shifts, shift swaps, '
               'rest checks',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['hr_work_entry', 'om_hr_base', 'om_hr_approval'],
    'data': [
        'security/om_hr_shift_security.xml',
        'security/ir.access.csv',
        'data/om_hr_shift_data.xml',
        'views/om_hr_shift_views.xml',
    ],
    'demo': ['demo/om_hr_shift_demo.xml'],
    'assets': {
        'web.assets_backend': [
            'om_hr_shift/static/src/**/*',
        ],
        'web.assets_tests': [
            'om_hr_shift/static/tests/tours/**/*',
        ],
    },
    'images': ['static/description/banner.gif'],
    'application': True,
}
