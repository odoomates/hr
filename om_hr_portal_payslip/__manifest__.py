{
    'name': 'HR Portal: Payslips',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employees read their payslips and download them as PDF on the website portal',
    'description': 'Adds a Payslips page to My HR on the website portal: the employees read their payslips once they '
                   'are done, line by line, and download the PDF. Installs by itself with HR Portal and Odoo 20 HR '
                   'Payroll. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_portal', 'om_hr_payroll'],
    'data': ['views/portal_templates.xml'],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
