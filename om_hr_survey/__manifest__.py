{
    'name': 'HR Pulse Surveys',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Anonymous pulse surveys and eNPS: one-time links that never tell who answered, results per '
               'department from five answers',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_base', 'survey'],
    'data': [
        'security/ir.access.csv',
        'data/survey_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'views/hr_pulse_views.xml',
    ],
    'demo': ['demo/om_hr_survey_demo.xml'],
    'images': ['static/description/banner.gif'],
}
