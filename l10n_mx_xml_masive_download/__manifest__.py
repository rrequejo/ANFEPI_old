# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'XML Masive Download',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
XML Masive Download from SAT WebService.
========================================

    """,
    'depends': ['l10n_mx_edi','account','base'],
    'data': [
        'security/ir.model.access.csv',
        'views/l10n_mx_edi_view.xml',
        'views/res_company_view.xml',
        'views/l10n_mx_edi_certificate_view.xml',
        'views/account_move_view.xml',
        'security/ir_rules.xml',
        'models/server_actions.xml',
    ],
    'auto_install': False,
    "license": "AGPL-3",
    # 'pre_init_hook': 'pre_init_hook',
}
