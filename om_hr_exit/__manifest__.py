{
    'name': 'HR Exit',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employee resignation and termination: approval, notice period, clearance checklist, exit interview',
    'description': 'An employee resigns from My HR, or HR records the end of a contract. The exit is approved '
                   'along an approval flow, the manager then HR by default. During the notice period each item of '
                   'the exit checklist is cleared by the people it names, with a to-do for each. HR then registers '
                   'the departure of the employee, and notes the exit interview. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_base', 'om_hr_approval'],
    'data': [
        'security/ir.access.csv',
        'data/om_hr_exit_data.xml',
        'views/om_hr_exit_checklist_views.xml',
        'views/om_hr_exit_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
    ],
    'images': ['static/description/banner.gif'],
}
