{
    'name': 'Shifts',
    'version': '1.0.0',
    'category': 'Human Resources/Shifts',
    'summary': 'Shift planning and rosters: shift templates, roster board, rotations, open shifts, shift swaps, '
               'rest checks',
    'description': 'Plan the shifts of the employees on a roster board, from shift templates or rotations such as '
                   '2 mornings, 2 nights, 2 days off. The roster warns of time off, unavailability, overlapping '
                   'shifts, too little rest and too many hours in a week. Published, the shifts are the working '
                   'schedule of the employees, which time off, attendances, overtime, lateness and payroll follow. '
                   'Employees see their shifts, claim open shifts, swap shifts with colleagues and tell the days '
                   'they cannot work. '
                   'Part of Odoo Mates HR.',
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
