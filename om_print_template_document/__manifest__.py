{
    'name': 'Print Templates: Documents',
    'version': '1.0.0',
    'category': 'Productivity',
    'summary': 'File the prints of a template as documents of the record, expiring after a number of days',
    'description': 'A print template may file each print as a document of the record printed, with the PDF and '
                   'an expiry date, e.g. a No Objection Certificate valid for 30 days: it shows on the documents '
                   'of the record and is reminded like any other document. Cancelling the print archives the '
                   'document. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_print_template', 'om_document'],
    'data': [
        'views/om_print_template_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
