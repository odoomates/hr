{
    'name': 'HR Base',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Shared base of the Odoo Mates HR modules: the My HR menu and the employee category of the contract',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['hr'],
    'data': [
        'views/hr_version_views.xml',
        'views/menu.xml',
    ],
    'images': ['static/description/banner.gif'],
    'pre_init_hook': 'pre_init_hook',
}
