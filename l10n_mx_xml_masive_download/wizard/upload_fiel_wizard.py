from odoo import models, fields, api
import base64
import requests
from odoo.exceptions import UserError
from io import BytesIO
import io

class UploadFileWizard(models.TransientModel):
    _name = 'upload.fiel.wizard'
    _description = 'Wizard to upload files'

    company_name = fields.Char(string='Company Name', readonly=True)
    vat_id = fields.Char(string='VAT ID', readonly=True)
    cer_file = fields.Binary(string='CER File', required=True)
    cer_filename = fields.Char(string='CER File Name')
    key_file = fields.Binary(string='KEY File', required=True)
    key_filename = fields.Char(string='KEY File Name')
    password = fields.Char(string='Password', required=True)

    @api.model
    def default_get(self, fields_list):
        """Override default_get to populate company and VAT fields."""
        res = super(UploadFileWizard, self).default_get(fields_list)
        company = self.env.company
        res.update({
            'company_name': company.name,
            'vat_id': company.vat,
        })
        return res
    
    

    def action_upload_files(self):


        

        files = {
            'cert_file': io.BytesIO(base64.b64decode(self.cer_file)),  # Directly send binary
            'key_file': io.BytesIO(base64.b64decode(self.key_file))  # Directly send binary
        }
        data = {
            'name': self.company_name,
            'RFC': self.vat_id,
            'password': self.password,
        }

        # Send POST request to the Flask server
        try:
            response = requests.post(
                'https://xmlsat.anfepi.com/upload-documents',
                data=data,
                files=files
            )
            response.raise_for_status()  # Check if the request was successful
        except requests.exceptions.RequestException as e:
            raise UserError(f"Error sending files: {e}")

        # Handle the server response
        if response.status_code == 200:
            return {'type': 'ir.actions.act_window_close'}
        else:
            raise UserError("Error al subir la información, verifique que este correcta ")

