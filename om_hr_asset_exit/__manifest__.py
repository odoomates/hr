{
    'name': 'HR Assets in Exits',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Exit clearance of the employee assets: an exit is cleared only once the assets are back',
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
