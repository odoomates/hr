{
    'name': 'HR Portal: Announcements',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employees read and acknowledge the announcements addressed to them on the website portal',
    'description': 'The announcements addressed to the employee, the important and unread ones first, read on the '
                   'website portal and acknowledged when asked. '
                   'Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_portal', 'om_hr_announcement'],
    'data': ['views/portal_templates.xml'],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
