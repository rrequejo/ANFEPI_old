from odoo import models, fields, api # type: ignore

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_mx_xml_download_api_key = fields.Char(
        related='company_id.l10n_mx_xml_download_api_key', 
        string='API Key', 
        readonly=False,
        )
    l10n_mx_xml_download_automatic_contact_creation = fields.Boolean(
        related='company_id.l10n_mx_xml_download_automatic_contact_creation', 
        string='Creacion automatica de contactos', 
        readonly=False,
        )