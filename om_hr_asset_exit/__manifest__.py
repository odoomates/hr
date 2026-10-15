{
    'name': 'HR Assets in Exits',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Exit clearance of the employee assets: an exit is cleared only once the assets are back',
    'description': 'When an exit is approved, each asset the employee holds becomes a line of its clearance, '
                   'with a to-do for the technician of the asset. The line is cleared when the asset is returned '
                   'or reported lost, and cannot be cleared by hand while the asset is still out. '
                   'Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_asset', 'om_hr_exit'],
    'data': [
        'views/om_hr_exit_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
