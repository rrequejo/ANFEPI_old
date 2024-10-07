# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'XML Masive Download',
    'version': '1.0',
    'category': 'Hidden',
    'author':'ANFEPI: Roberto Requejo Fernández',
    'description': """
XML Masive Download from SAT WebService.
========================================

    """,
    'depends': ['l10n_mx_edi','account','base'],
    'data': [
        'security/ir.model.access.csv',
        'security/groups.xml',
        'views/l10n_mx_edi_view.xml',
        'views/res_company_view.xml',
        'views/account_move_view.xml',
        'views/custom_accounting_settings_view.xml',
        'security/ir_rules.xml',
        'models/server_actions.xml',
        'report/product_report.xml',
        'report/ir_actions_report.xml',
        #'report/reporte_conciliacion_view.xml',
        'wizard/invoice_wizard_views.xml',
        #'wizard/conciliaton_report_wizard_views.xml',
        'wizard/upload_fiel_wizard.xml'
        
    ],
    'images': ['static/description/icon.png'],
    'auto_install': False,
    "license": "AGPL-3",

}