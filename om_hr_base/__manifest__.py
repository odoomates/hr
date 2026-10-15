{
    'name': 'HR Base',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Shared base of the Odoo Mates HR modules: the My HR menu and the employee category of the contract',
    'description': 'What the Odoo Mates HR modules have in common: the My HR menu, where each module adds what '
                   'the employees do for themselves, and the employee category of the contract with the Employee '
                   'Types menu. Records that move here from another Odoo Mates HR module keep their database id. '
                   'Part of Odoo Mates HR.',
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
