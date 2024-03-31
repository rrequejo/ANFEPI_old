from odoo import api, fields, models, tools
from odoo.exceptions import UserError
import base64
from lxml import etree
from lxml.objectify import fromstring

class AccountMove(models.Model):
    _inherit = 'account.move'

    xml_imported = fields.Boolean(string="XML Imported", default=False)
    stored_sat_uuid = fields.Char(compute='_get_uuid_from_xml_attachment', string="CFDI UUID", store=True, index=True, default=False)

    """
    Method created to have a field that stores the UUID of the CFDI in the account.move model
    To be able to relate the downloaded xml with the invoice
    """
    @api.depends('attachment_ids')
    def _get_uuid_from_xml_attachment(self):
        for record in self:
            attachments = record.attachment_ids.filtered(lambda x: x.mimetype == 'application/xml')
            if attachments:
                try: 
                    # Obtain uuid
                    cfdi_data = _l10n_mx_edi_decode_cfdi(attachments[0].datas)
                    record.stored_sat_uuid = cfdi_data['uuid']
                except:
                    pass
            else:
                record.stored_sat_uuid = False

    @api.onchange('state')
    def _onchange_update_downloaded_xml_record(self):
        downloaded_xml = self.env['account.edi.downloaded.xml.sat'].search([('invoice_id', '=', self.id)], limit=1)
        if downloaded_xml:
            downloaded_xml.write({'state': self.state})        

    # This method was moved to DownloadedXmlSat --> delete later 
    def relate_download(self):
        domain = [('state', '=', 'draft')]
        to_relate = self.env['account.edi.downloaded.xml.sat'].search(domain)
        
        for download in to_relate: 
            domain = [('state', 'not in', ['cancel', 'draft']), ('l10n_mx_edi_cfdi_uuid', '=', download.name)]
            move = self.env['account.move'].search(domain)
            if len(move) == 1:
                download.write({'invoice_id':move.id, 'state': move.state})
            else:
                download.write({'state': 'error'})

    def generate_pdf_attatchment(self):
        pdf = self.env.ref('account.account_invoices')._render_qweb_pdf('account.report_invoice',self.id)
        b64_pdf = base64.b64encode(pdf[0])

        ir_values = {
            'name': 'Invoice ' + self.name,
            'type': 'binary',
            'datas': b64_pdf,
            'store_fname': 'Invoice ' + self.name + '.pdf',
            'mimetype': 'application/pdf',
            'res_model': 'account.move',
            'res_id': self.id,
        }
       
        self.env['ir.attachment'].create(ir_values)

    # This methos was taken from odoo 16.0 
    def _l10n_mx_edi_decode_cfdi(self, cfdi_data=None):
        ''' Helper to extract relevant data from the CFDI to be used, for example, when printing the invoice.
        :param cfdi_data:   The optional cfdi data.
        :return:            A python dictionary.
        '''
        self.ensure_one()

        def is_purchase_move(move):
            return move.move_type in move.get_purchase_types() \
                    or move.payment_id.reconciled_bill_ids

        # Find a signed cfdi.
        if not cfdi_data:
            signed_edi = self._get_l10n_mx_edi_signed_edi_document()
            if signed_edi:
                cfdi_data = base64.decodebytes(signed_edi.sudo().attachment_id.with_context(bin_size=False).datas)

            # For vendor bills, the CFDI XML must be posted in the chatter as an attachment.
            elif is_purchase_move(self) and self.country_code == 'MX' and not self.l10n_mx_edi_cfdi_request:
                attachments = self.attachment_ids.filtered(lambda x: x.mimetype == 'application/xml')
                if attachments:
                    attachment = sorted(attachments, key=lambda x: x.create_date)[-1]
                    cfdi_data = base64.decodebytes(attachment.with_context(bin_size=False).datas)

        # Nothing to decode.
        if not cfdi_data:
            return {}

        try:
            cfdi_node = fromstring(cfdi_data)
        except etree.XMLSyntaxError:
            # Not an xml
            return {}

        return self._l10n_mx_edi_decode_cfdi_etree(cfdi_node)
    
    # This methos was taken from odoo 16.0 
    def _l10n_mx_edi_decode_cfdi_etree(self, cfdi_node):
        ''' Helper to extract relevant data from the CFDI etree object, does not require a move record.
        :param cfdi_node:   The cfdi etree object.
        :return:            A python dictionary.
        '''
        def get_node(cfdi_node, attribute, namespaces):
            if hasattr(cfdi_node, 'Complemento'):
                node = cfdi_node.Complemento.xpath(attribute, namespaces=namespaces)
                return node[0] if node else None
            else:
                return None

        def get_cadena(cfdi_node, template):
            if cfdi_node is None:
                return None
            cadena_root = etree.parse(tools.file_open(template))
            return str(etree.XSLT(cadena_root)(cfdi_node))

        try:
            emisor_node = cfdi_node.Emisor
            receptor_node = cfdi_node.Receptor
        except AttributeError:
            # Not an xml object or not a valid CFDI
            return {}

        tfd_node = get_node(
            cfdi_node,
            'tfd:TimbreFiscalDigital[1]',
            {'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'},
        )

        return {
            'uuid': ({} if tfd_node is None else tfd_node).get('UUID'),
            'supplier_rfc': emisor_node.get('Rfc', emisor_node.get('rfc')),
            'customer_rfc': receptor_node.get('Rfc', receptor_node.get('rfc')),
            'amount_total': cfdi_node.get('Total', cfdi_node.get('total')),
            'cfdi_node': cfdi_node,
            'usage': receptor_node.get('UsoCFDI'),
            'payment_method': cfdi_node.get('formaDePago', cfdi_node.get('MetodoPago')),
            'bank_account': cfdi_node.get('NumCtaPago'),
            'sello': cfdi_node.get('sello', cfdi_node.get('Sello', 'No identificado')),
            'sello_sat': tfd_node is not None and tfd_node.get('selloSAT', tfd_node.get('SelloSAT', 'No identificado')),
            'certificate_number': cfdi_node.get('noCertificado', cfdi_node.get('NoCertificado')),
            'certificate_sat_number': tfd_node is not None and tfd_node.get('NoCertificadoSAT'),
            'expedition': cfdi_node.get('LugarExpedicion'),
            'fiscal_regime': emisor_node.get('RegimenFiscal', ''),
            'emission_date_str': cfdi_node.get('fecha', cfdi_node.get('Fecha', '')).replace('T', ' '),
            'stamp_date': tfd_node is not None and tfd_node.get('FechaTimbrado', '').replace('T', ' '),
        }