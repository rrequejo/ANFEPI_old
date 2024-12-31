from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
import xml.etree.ElementTree as ET
import base64
from lxml import etree



class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    cfdi_uuid = fields.Char(string="CFDI UUID", index=True, unique=True, help="UUID del CFDI extraído del archivo XML")

    @api.model
    def create(self, vals):
        if vals.get('raw'):
            raw_data = vals.get('raw')
            cfdi_decoded = self.env['l10n_mx_edi.document']._decode_cfdi_attachment(raw_data)
            cfdi_uuid = cfdi_decoded.get('uuid')
            if cfdi_uuid:
                vals['cfdi_uuid'] = cfdi_uuid

        res = super(IrAttachment, self).create(vals)
        print("\n\n\n")
        print(vals)
        print(cfdi_uuid)
        return res