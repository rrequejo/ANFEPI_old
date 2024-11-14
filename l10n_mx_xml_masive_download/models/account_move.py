from odoo import api, fields, models, tools
from odoo.exceptions import UserError
import base64
from lxml import etree
import xml.etree.ElementTree as ET

USO_CFDI  = [
    ("G01", "Adquisición de mercancías"),
    ("G02", "Devoluciones, descuentos o bonificaciones"),
    ("G03", "Gastos en general"),
    ("I01", "Construcciones"),
    ("101", "Construcciones"),
    ("I02", "Mobiliario y equipo de oficina por inversiones"),
    ("I03", "Equipo de transporte"),
    ("I04", "Equipo de cómputo y accesorios"),    
    ("105", "Dados, troqueles, moldes, matrices y herramental"),
    ("106", "Comunicaciones telefónicas"),
    ("107", "Comunicaciones satelitales"),
    ("108", "Otra maquinaria y equipo"),
    ("D01", "Honorarios médicos, dentales y gastos hospitalarios"),
    ("D02", "Gastos médicos por incapacidad o discapacidad"),
    ("D03", "Gastos funerales"),
    ("D04", "Donativos"),
    ("D05", "Intereses reales efectivamente pagados por créditos hipotecarios (casa habitación)"),
    ("D06", "Aportaciones voluntarias al SAR"),
    ("D07", "Primas por seguros de gastos médicos"),
    ("D08", "Gastos de transportación escolar obligatoria"),
    ("D09", "Depósitos en cuentas para el ahorro, primas que tengan como base planes de pensiones"),
    ("D10", "Pagos por servicios educativos (colegiaturas)"),
    ("CP01", "Pagos"),
    ("CN01", "Nómina"),
    ("S01", "Sin Efectos Fiscales"),
]

class AccountMove(models.Model):
    _inherit = 'account.move'

    stored_sat_uuid = fields.Char(
        compute='_get_uuid_from_xml_attachment', 
        string="CFDI UUID", 
        store=True, 
        )
    xml_imported_id = fields.Many2one('account.edi.downloaded.xml.sat', string="Downloaded XML")


    payment_method = fields.Selection([('PPD','PPD'),('PUE','PUE')], string='Metodo de Pago')
    uso_sat = fields.Selection(USO_CFDI, string="Uso CFDI")

    """
    Method created to have a field that stores the UUID of the CFDI in the account.move model
    To be able to relate the downloaded xml with the invoice
    """
    @api.depends('attachment_ids')
    def _get_uuid_from_xml_attachment(self):
        for record in self:
            if not record.stored_sat_uuid:
                attachments = record.attachment_ids.filtered(lambda x: x.mimetype == 'application/xml')
                if attachments:
                    for attatchment in attachments:
                        try:
                            xml_content = base64.b64decode(attatchment.datas)
                            root = ET.fromstring(xml_content)
                            uuid = root.find('.//{http://www.sat.gob.mx/TimbreFiscalDigital}TimbreFiscalDigital').attrib['UUID']
                            print("UUID: "+str(uuid))
                            record.stored_sat_uuid = uuid
                            break
                        except: 
                            record.stored_sat_uuid = False
            else: 
                record.stored_sat_uuid = False


    # def _get_default_uuid_from_xml_attachment(self):
    #     for record in self:
    #         if not record.stored_sat_uuid:
    #             attachments = record.attachment_ids.filtered(lambda x: x.mimetype == 'application/xml')
    #             if attachments:
    #                 for attachment in attachments:
    #                     try:
    #                         xml_content = base64.b64decode(attachment.datas)
    #                         root = ET.fromstring(xml_content)
    #                         uuid = root.find('.//{http://www.sat.gob.mx/TimbreFiscalDigital}TimbreFiscalDigital').attrib['UUID']
    #                         print("UUID: "+str(uuid))
    #                         break
    #                         record.stored_sat_uuid = uuid
    #                     except: 
    #                         record.stored_sat_uuid = False

    @api.constrains('state')
    def onchange_update_downloaded_xml_record(self):
        if self.xml_imported_id:
            self.xml_imported_id.write({'state':self.state})   

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

    def create_edi_document_from_attatchment(self, uuid):
        edi = self.env['l10n_mx_edi.document']
        edi_content = self.attachment_ids.filtered(lambda m: m.mimetype == 'application/xml')
        if edi_content:
            edi_data = {
                'state' : 'invoice_sent',
                'datetime': fields.Datetime.now(),
                'attachment_uuid':uuid,
                'attachment_id':edi_content.id,
                'move_id': self.id,
            }
            new_edi_doc = edi.create(edi_data)

            # Asociar las facturas
            new_edi_doc.invoice_ids = [(6, 0, [self.id])]  # A lo mejor es aqui, en vez de poner ".invoice_ids" poner payment 


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