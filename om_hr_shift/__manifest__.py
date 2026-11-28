{
    'name': 'Shifts',
    'version': '20.0.1.0.3',
    'category': 'Human Resources/Shifts',
    'summary': 'Shift planning and rosters on the planning Gantt: shift templates, rotations, open shifts, '
               'shift swaps, unavailability, rest checks',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_planning', 'om_planning_hr', 'hr_work_entry', 'om_hr_base', 'om_hr_approval'],
    'data': [
        'security/om_hr_shift_security.xml',
        'security/ir.access.csv',
        'data/om_hr_shift_migration.xml',
        'data/om_hr_shift_data.xml',
        'views/om_hr_shift_views.xml',
    ],
    'demo': ['demo/om_hr_shift_demo.xml'],
    'images': ['static/description/banner.gif'],
    'application': True,
}
