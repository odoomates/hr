{
    'name': 'HR Appraisals',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employee appraisals: self assessment, manager review, rating, goals, probation reviews and '
               'review cycles',
    'description': 'Appraise the employees: they assess themselves, their manager reviews and rates them, and '
                   'they set goals for the next period. Each side reads the feedback of the other only when it is '
                   'their turn. Probation reviews are created before the trial period ends, appraisals are planned '
                   'at a regular interval, and review cycles create them for whole departments. A raise or a '
                   'promotion decided is recorded as a new version of the contract. '
                   'Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_base', 'mail'],
    'data': [
        'security/ir.access.csv',
        'data/om_hr_appraisal_data.xml',
        'wizard/om_hr_appraisal_version_views.xml',
        'views/om_hr_appraisal_views.xml',
        'views/om_hr_appraisal_cycle_views.xml',
        'views/om_hr_appraisal_goal_views.xml',
        'views/om_hr_appraisal_config_views.xml',
        'views/hr_employee_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
    ],
    'images': ['static/description/banner.gif'],
}
