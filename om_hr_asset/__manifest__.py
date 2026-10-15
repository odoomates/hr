{
    'name': 'HR Assets',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employee assets and equipment: handover with a signed form, return, loss, charges and history',
    'description': 'The laptops, phones and tools of the company, as the equipment of the Maintenance app, '
                   'handed over to the employees with a signed handover form, returned with their condition or '
                   'reported lost, with an optional charge to the employee and the history of who held each '
                   'asset. Employees see the assets in their hands in My HR. '
                   'Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['hr_maintenance', 'om_hr_base', 'om_print_template'],
    'data': [
        'security/ir.access.csv',
        'data/om_hr_asset_data.xml',
        'views/maintenance_equipment_views.xml',
        'views/om_hr_asset_assignment_views.xml',
        'views/hr_employee_views.xml',
        'views/menu.xml',
    ],
    'images': ['static/description/banner.gif'],
}
