from odoo import models, fields # type: ignore

class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_mx_xml_download_api_key = fields.Char(string='API Key')
    l10n_mx_xml_download_automatic_contact_creation = fields.Boolean(string='API Key', default=False)