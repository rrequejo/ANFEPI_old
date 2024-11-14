from odoo import models, fields # type: ignore

class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_mx_xml_download_api_key = fields.Char(string='API Key')
    l10n_mx_xml_download_automatic_contact_creation = fields.Boolean(string='API Key', default=False)

    def action_open_upload_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Upload Fiel',
            'res_model': 'upload.fiel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_id': self.id,
            },
        }