{
    'name': 'HR Portal: Appraisals',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employees fill in their self assessment and update the progress of their goals on the website portal',
    'description': 'Adds an Appraisals page to My HR on the website portal: the employees write and submit their self '
                   'assessment, read the review of their manager once the appraisal is done, and update the progress '
                   'of their goals. Installs by itself with HR Portal and HR Appraisals. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_portal', 'om_hr_appraisal'],
    'data': ['views/portal_templates.xml'],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
