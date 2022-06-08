# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta

from lxml import etree as et
import xmltodict
import base64
from xml.dom.minidom import parse, parseString
import requests
import zipfile
import os
import tempfile
import io
from suds.client import Client
import random, pdb
import logging
_logger = logging.getLogger(__name__)

class XmlImportWizard(models.TransientModel):
    _name = 'xml.import.wizard'
    _description ="Importador de archivos XML de CFDIs"
    _check_company_auto = True
    
    import_type = fields.Selection([
     ('start_amount', 'Saldos Iniciales'),
     ('regular', 'Factura regular')],
      string='Tipo de Importacion',
      required=True,
      default='regular')
    invoice_type = fields.Selection([
     ('out_invoice', 'Cliente'),
     ('in_invoice', 'Proveedor')],
      string='Tipo de factura',
      required=True,
      default='out_invoice')
    line_account_id = fields.Many2one('account.account', string='Cuenta de Ingreso o Gasto',
      required=True,
      help='Si la empresa no tiene definida una cuenta de importacion xml por defecto, se usara esta')
    invoice_account_id = fields.Many2one('account.account', string='Cuenta Contable para Empresa',
      required=True)
    line_analytic_account_id = fields.Many2one('account.analytic.account', string='Cuenta analitica de linea',
      required=False)
    journal_id = fields.Many2one('account.journal', string='Diario',
      required=True)
    line_analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Etiquetas analiticas',
      required=False)
    team_id = fields.Many2one('crm.team', string='Equipo de ventas')
    user_id = fields.Many2one('res.users', string='Comercial')
    uploaded_file = fields.Binary(string='Archivo ZIP', required=True)
    filename = fields.Char(string='Nombre archivo')
    sat_validation = fields.Boolean(string='Validar en SAT', default=True)
    create_product = fields.Boolean(string='Crear productos', help='Si el producto no se encuentra en Odoo, crearlo automaticamente',
      default=True)

    search_by = fields.Selection([
     ('default_code', 'Referencia Interna'),
     ('unspsc_code', 'Clave SAT')],
      string='Busqueda de Productos por',
      required=True,
      default='default_code')

    company_id = fields.Many2one('res.company', 'Company', default=(lambda self: self.env.company),
      required=True)
    payment_term_id = fields.Many2one('account.payment.term',
      string='Plazo de pago',
      help='Se utilizara este plazo de pago para las empresas creadas automaticamente, \n si no se especifica, se usara el de 15 dias')
    description = fields.Char(string='Referencia/Descripcion')

    @api.onchange('user_id')
    def _onchange_user_id(self):
        self.team_id = self.user_id.sale_team_id.id

    @api.onchange('invoice_type', 'company_id')
    def _onchange_invoice_type(self):
        """
        DATOS POR DEFECTO, POR USUARIO
        obtiene datos de la ultima factura
        creada por el usuario
        no cancelada
        de la compañia 
        """
        company_id = self.env.user.company_id
        
        domain = {}
        if self.invoice_type=='out_invoice':
            domain['invoice_account_id'] = [('user_type_id.type','=','receivable')]
            domain['journal_id'] = [('type','=','sale')]
            self.user_id = self.env.user.id
            self.journal_id = self.env['account.journal'].search([('type','=','sale')], limit=1)
            self.invoice_account_id = self.env['account.account'].search([('internal_type', '=', 'receivable'), ('deprecated', '=', False)], limit=1, order='id asc')
            self.line_account_id = self.journal_id.default_account_id.id

            
        else:
            domain['invoice_account_id'] = [('user_type_id.type','=','payable')]
            domain['journal_id'] = [('type','=','purchase')]
            self.team_id = False
            self.user_id = False
            self.journal_id = self.env['account.journal'].search([('type','=','purchase')], limit=1)
            self.invoice_account_id = self.env['account.account'].search([('internal_type', '=', 'payable'), ('deprecated', '=', False)], limit=1, order='id asc')
            self.line_account_id = self.journal_id.default_account_id.id
            
        return {'domain': domain}
        

    def check_status_sat(self, obj_xml):
        uuid = False
        #-------------
        body = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/"><soapenv:Header/><soapenv:Body><tem:Consulta><!--Optional:--><tem:expresionImpresa><![CDATA[?re={0}&rr={1}&tt={2}&id={3}]]></tem:expresionImpresa></tem:Consulta></soapenv:Body></soapenv:Envelope>
        """
        url = 'https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc?wsdl'
        headers = {'Content-type': 'text/xml;charset="utf-8"', 
                   'Accept' : 'text/xml', 
                   'SOAPAction': 'http://tempuri.org/IConsultaCFDIService/Consulta'}
        #-------------

        #xml_data = obj_xml.replace(b'http://www.sat.gob.mx/registrofiscal ', b'').replace(b'http://www.sat.gob.mx/cfd/3 ', b'').replace(b'Rfc=',b'rfc=').replace(b'Fecha=',b'fecha=').replace(b'Total=',b'total=').replace(b'Folio=',b'folio=').replace(b'Serie=',b'serie=')
        result, res = False, False
        estado_cfdi = ''
        try:
            uuid, rfc_emisor, rfc_receptor, total = obj_xml['uuid'], obj_xml['rfc_emisor'], obj_xml['rfc_receptor'], obj_xml['total']
            #-------------
            bodyx = body.format(rfc_emisor, rfc_receptor, total, uuid)
            result = requests.post(url=url, headers=headers, data=bodyx)
            res = xmltodict.parse(result.text)
            if result.status_code == 200:
                estado_cfdi = res['s:Envelope']['s:Body']['ConsultaResponse']['ConsultaResult']['a:Estado']
                _logger.info("\nFolio: %s\nRFC Emisor: %s\nRFC Receptor: %s\nTotal: %s\nEstado: %s" % (uuid, rfc_emisor, rfc_receptor, total,estado_cfdi))
                
            else:
                raise UserError(_('No Puede Validar la Factura o Nota de Credito, error en la llamada al WebService del SAT: .\n\n'
                      'Codigo Estatus: %s\n'
                      'Folio Fiscal: %s\n'
                      'RFC Emisor: %s\n'
                      'RFC Receptor: %s\n'
                      'Monto Total: %d') % (result.status_code, uuid, rfc_emisor, rfc_receptor, total))
            #-------------
        except Exception as e:
            raise UserError('Error al verificar el estatus de la factura: ' + str(e))
        return estado_cfdi

    
    def validate_bills(self):
        """
            Función principal. Controla todo el flujo de 
            importación al clickear el botón (parsea el archivo
            subido, lo valida, obtener datos de la factura y
            guardarla crea factura en estado de borrador).
        """
        edi_obj = self.env['account.edi.document']
        edi_cfdi33 = self.env['account.edi.format'].search([('code','=','cfdi_3_3')], limit=1)
        file_ext = self.get_file_ext(self.filename)
        if file_ext.lower() not in ('xml', 'zip'):
            raise ValidationError('Por favor, escoja un archivo ZIP o XML')
        else:
            raw_file = self.get_raw_file()
            zip_file = self.get_zip_file(raw_file)
            if zip_file:
                bills = self.get_xml_from_zip(zip_file)
            else:
                bills = self.get_xml_data(raw_file)
        for bill in bills:
            #try:
            invoice, invoice_line, version = self.prepare_invoice_data(bill)
            #except:
            #    raise ValidationError('Verifique que la estructura del siguiente archivo sea correcta: ' + bill['filename'])

            bill['invoice_data'] = invoice
            bill['invoice_line_data'] = invoice_line
            bill['version'] = version
            if invoice['tipo_comprobante'] != 'P':
                bill['valid'] = True
            else:
                bill['valid'] = False
                bill['state'] = 'Tipo de comprobante no valido: "P"'

        filtered_bills = self.get_vat_validation(bills)
        if self.sat_validation:
            filtered_bills = self.get_sat_validation(bills)
        self.show_validation_results_to_user(filtered_bills)
        invoice_ids = []
        for bill in bills:
            invoice = bill['invoice_data']
            invoice_line = bill['invoice_line_data']
            version = bill['version']
            uuid_name = invoice['uuid']
            if not self.validate_duplicate_invoice(invoice['rfc'], invoice['amount_total'], invoice['date_invoice'], invoice['name']):
                draft = self.create_bill_draft(invoice, invoice_line, uuid_name)
                if self.invoice_type == 'out_invoice' or self.invoice_type == 'out_refund':
                    draft.invoice_payment_term_id = draft.partner_id.property_payment_term_id
                else:
                    draft.invoice_payment_term_id = draft.partner_id.property_supplier_payment_term_id
                if not draft.invoice_payment_term_id:
                    draft.invoice_date_due = draft.invoice_date
                if self.import_type == 'regular':
                    if self.invoice_type == 'in_invoice':
                        draft.narration = self.description or ''
                attachment = self.attach_to_invoice(draft, bill['xml_file_data'], bill['filename'], uuid_name)
                _logger.info("attachment.datas: %s" %  attachment.datas)
                #draft.l10n_mx_edi_cfdi_name = bill['filename']
                invoice_ids.append(draft.id)
                # Agregar info para EDI
                
                xedi = edi_obj.create({'name' : uuid_name+'.xml',
                                       'state' : 'sent',
                                       'edi_format_name' : edi_cfdi33.name,
                                       'edi_format_id' : edi_cfdi33.id,
                                       'attachment_id' : attachment.id,
                                       'move_id'    : draft.id
                                      })
                

        return self.action_view_invoices(invoice_ids)

    def action_view_invoices(self, invoice_ids):
        self.ensure_one()
        _logger.info("\n###### invoice_ids: %s" % invoice_ids)
        if not invoice_ids:
            return False
        if self.invoice_type == 'out_invoice':
            ### Rertorno de la información ###
            if len(invoice_ids) > 1:
                imd = self.env['ir.model.data']
                action_ref = imd._xmlid_to_res_model_res_id('account.action_move_out_invoice_type')
                action = self.env[action_ref[0]].browse(action_ref[1])
                form_view_id = imd._xmlid_to_res_id('account.view_move_form')
                list_view_id = imd._xmlid_to_res_id('account.view_out_invoice_tree')
                action_invoices = self.env.ref('account.action_move_out_invoice_type')
                action = action_invoices.read()[0]
                return {
                            'name': 'Facturas',
                            'type': 'ir.actions.act_window',
                            'view_mode': 'tree,form',
                            'view_type': 'form',
                            'res_model': 'account.move',
                            'domain': [('id', 'in',invoice_ids)],
                            'context': {'create': False, 'tree_view_ref': 'account.view_out_invoice_tree'},
                        }
            else:
                return {
                            'name': _('Factura Global'),
                            'view_mode': 'form',
                            'view_id': self.env.ref('account.view_move_form').id,
                            'res_model': 'account.move',
                            'context': "{}", # self.env.context
                            'type': 'ir.actions.act_window',
                            'res_id': invoice_ids[0],
                        }

        else:
            if len(invoice_ids) > 1:
                imd = self.env['ir.model.data']
                action_ref = imd._xmlid_to_res_model_res_id('account.action_move_in_invoice_type')
                action = self.env[action_ref[0]].browse(action_ref[1])
                form_view_id = imd._xmlid_to_res_id('account.view_move_form')
                list_view_id = imd._xmlid_to_res_id('account.view_in_invoice_tree')
                action_invoices = self.env.ref('account.action_move_in_invoice_type')
                action = action_invoices.read()[0]
                return {
                            'name': 'Facturas',
                            'type': 'ir.actions.act_window',
                            'view_mode': 'tree,form',
                            'view_type': 'form',
                            'res_model': 'account.move',
                            'domain': [('id', 'in',invoice_ids)],
                            'context': {'create': False, 'tree_view_ref': 'account.view_in_invoice_tree'},
                        }
            else:
                return {
                            'name': _('Factura Global'),
                            'view_mode': 'form',
                            'view_id': self.env.ref('account.view_move_form').id,
                            'res_model': 'account.move',
                            'context': "{}", # self.env.context
                            'type': 'ir.actions.act_window',
                            'res_id': invoice_ids[0],
                        }

    def validate_duplicate_invoice(self, vat, amount_total, date, invoice_name):
        """
        REVISA SI YA EXISTE LA FACTURA EN SISTEMA
        DEVUELVE TRUE SI YA EXISTE
        FALSE SI NO
        """
        date = date.split('T')[0]
        AccountInvoice = self.env['account.move'].sudo()
        domain = [
         (
          'partner_id.vat', '=', vat),
         (
          'amount_total', '=', round(float(amount_total), 2)),
         (
          'invoice_date', '=', date),
         ('state', '!=', 'cancel')]
        if self.invoice_type == 'out_invoice' or self.invoice_type == 'out_refund':
            domain.append(('name', '=', invoice_name))
        else:
            domain.append(('ref', '=', invoice_name))
        invoices = AccountInvoice.search(domain)
        return bool(invoices)
        #test_invoice = AccountInvoice.search([('id', '=', 3048)])
        if invoices:
            return True
        else:
            return False

    def get_raw_file(self):
        """Convertir archivo binario a byte string."""
        return base64.b64decode(self.uploaded_file)

    def get_zip_file(self, raw_file):
        """
            Convertir byte string a archivo zip
            Valida y tira errorsi el archivo subido 
            no era un zip.
        """
        try:
            zf = zipfile.ZipFile(io.BytesIO(raw_file), 'r')
            return zf
        except zipfile.BadZipFile:
            return False

    def get_xml_data(self, file):
        """
            Ordena datos de archivo xml
        """
        xmls = []
        xml = xmltodict.parse(file.decode('utf-8'))
        xml_file_data = base64.encodestring(file)
        bill = {'filename':self.filename, 
         'xml':xml, 
         'xml_file_data':xml_file_data}
        xmls.append(bill)
        return xmls

    def get_file_ext(self, filename):
        """
        obtiene extencion de archivo, si este lo tiene
        fdevuelve false, si no cuenta con una aextension
        (no es archivo entonces)
        """
        file_ext = filename.split('.')
        if len(file_ext) > 1:
            file_ext = filename.split('.')[1]
            return file_ext
        else:
            return False

    def get_xml_from_zip(self, zip_file):
        """
            Extraer archivos del .zip.
            Convertir XMLs a diccionario para 
            un manejo mas fácil de los datos.
        """
        xmls = []
        for fileinfo in zip_file.infolist():
            file_ext = self.get_file_ext(fileinfo.filename)
            if file_ext in ('xml', 'XML'):
                xml = xmltodict.parse(zip_file.read(fileinfo).decode('utf-8'))
                xml_file_data = zip_file.read(fileinfo)
                
                _logger.info("\nxml_file_data: %s" % xml_file_data)
                #xml_file_data = base64.encodestring(zip_file.read(fileinfo))
                bill = {'filename':fileinfo.filename, 
                 'xml':xml, 
                 'xml_file_data':xml_file_data}
                xmls.append(bill)

        return xmls

    def check_vat(self, rfc_emisor, rfc_receptor):
        """
        comprueba que el rfc emisor/receptor
        concuerde con la compañia a la que se cargara
        la factura, dependiendo si es de entrada o salida
        regresa True si coincide, False si no
        """
        if self.invoice_type == 'out_invoice' or self.invoice_type == 'out_refund':
            if self.company_id.vat != rfc_emisor:
                return False
        elif self.company_id.vat != rfc_receptor:
            return False
        return True

    def get_vat_validation(self, bills):
        """
        valida que los rfcs coincidan
        con lso registrados en odoo
        regresa bills con datos extra
        """
        for bill in bills:
            invoice = bill['invoice_data']
            invoice_line = bill['invoice_line_data']
            version = bill['version']
            xml_dict = self.get_vat_dict(bill)
            if not self.check_vat(xml_dict['rfc_emisor'], xml_dict['rfc_receptor']):
                bill['valid'] = False
                bill['state'] = 'RFC no coincide con compañia'

        return bills

    def get_vat_dict(self, bill):
        """
        devuelve diccionario con datos de rfc emisor, receptor
        uuid y total
        """
        self.ensure_one()
        xml_dict = {}
        invoice = bill['invoice_data']
        invoice_line = bill['invoice_line_data']
        version = bill['version']
        if self.invoice_type == 'out_invoice' or self.invoice_type == 'out_refund':
            xml_dict = {'rfc_emisor':invoice['company_rfc'],  'rfc_receptor':invoice['rfc'], 
             'total':invoice['amount_total'], 
             'uuid':invoice['uuid']}
        else:
            xml_dict = {'rfc_emisor':invoice['rfc'],  'rfc_receptor':invoice['company_rfc'], 
             'total':invoice['amount_total'], 
             'uuid':invoice['uuid']}
        return xml_dict

    def get_sat_validation(self, bills):
        """
        valida que factura exista en sat
        y devuelve un diccionario indicadondo
        el estado y si es valida
        """
        for bill in bills:
            invoice = bill['invoice_data']
            invoice_line = bill['invoice_line_data']
            version = bill['version']
            xml_dict = self.get_vat_dict(bill)
            state = self.check_status_sat(xml_dict)
            bill['valid'] = True
            bill['state'] = state
            if state != 'Vigente':
                bill['valid'] = False
                bill['state'] = state

        return bills

    def get_tax_ids(self, tax_group, version='3.3'):
        """
        obtiene los ids de los impuestos
        a partir de nombres de grupos de impuestos
        estructura:
        000|0.16,001|0.0,
        regresa [(6, None, ids)]
        """
        tax_ids = []
        AccountTax = self.env['account.tax'].sudo()
        if self.invoice_type == 'out_invoice' or self.invoice_type == 'out_refund':
            type_tax_use = 'sale'
        else:
            type_tax_use = 'purchase'
        tax_group = tax_group[:-1]
        taxes = tax_group.split(',')
        for tax in taxes:
            if tax:
                tax_data = tax.split('|')
                tax_number = tax_data[0]
                tax_type = tax_data[2]
                domain = [
                 (
                  'type_tax_use', '=', type_tax_use),
                 (
                  'company_id', '=', self.company_id.id)]
                tax_factor = False
                if len(tax_data) == 4:
                    tax_factor = tax_data[3]
                    domain.append(('l10n_mx_tax_type', '=', tax_factor))
                if version == '3.3':
                    if tax_factor != 'Exento':
                        tax_rate = float(tax_data[1])
                        if tax_type == 'tras':
                            rate = tax_rate * 100
                        else:
                            rate = -(tax_rate * 100)
                        domain.append(('amount', '=', rate))
                    domain.append(('tax_code_mx', '=', tax_number))
                else:
                    if tax_data[1] != 'xxx':
                        tax_rate = float(tax_data[1])
                        if tax_type == 'tras':
                            rate = tax_rate
                        else:
                            rate = -tax_rate
                        domain.append(('amount', '=', rate))
                    domain.append(('name', 'ilike', tax_number))
                _logger.info("\ntax domain: %s" % domain)
                tax_id = AccountTax.search(domain)
                if tax_id:
                    tax_id = tax_id[0].id
                    tax_ids.append(tax_id)

        if tax_ids:
            return [
             (
              6, None, tax_ids)]
        else:
            return False

    def attach_to_invoice(self, invoice, xml, xml_name, uuid_file=False):
        """
        adjunta xml a factura
        """

        xml_decode = base64.b64decode(xml)
        _logger.info("\n#### xml_name: %s" % xml_name)
        _logger.info("\n#### xml: %s" % xml)
        (fileno, fname) = tempfile.mkstemp('.xml', 'tmp')
        os.close(fileno)

        #### Escribimos el resultado en el Archivo Temporal ####
        f_write = open(fname, 'w')
        f_write.write(xml.decode("utf-8"))
        f_write.close()

        #### Convertimos el archivo a base64 ####
        f_read = open(fname, "rb")
        fdata = f_read.read()
        out_b64 = base64.encodebytes(fdata)
        if not '.xml' in xml_name:
            xml_name = xml_name+'.xml'
        vals = {
            'res_model' : 'account.move', 
            'res_id'    : invoice.id, 
            'name'      : uuid_file+'.xml' if uuid_file else xml_name, 
            #'datas'       : base64.encodebytes(str.encode(xml)),
            'datas'     : out_b64,
            #'datas'     : base64.encodebytes(xml),
            'type'      : 'binary',
            'store_fname': xml_name,
        }
        IrAttachment = self.env['ir.attachment'].sudo()
        _logger.info("\n#### attachment vals: %s" % vals)
        attachment = IrAttachment.create(vals)
        return attachment

    def prepare_invoice_data(self, bill):
        """
            Obtener datos del XML y wizard para llenar factura
            Returns:
                invoice: datos generales de la factura.
                invoice_line: conceptos de la factura.
        """
        invoice = {}
        invoice_line = []
        partner = {}
        filename = bill['filename']
        root = bill['xml']['cfdi:Comprobante']
        version = root.get('@Version') or root.get('@version') or ''
        if self.invoice_type == 'out_invoice' or self.invoice_type == 'out_refund':
            vendor = root['cfdi:Receptor']
            vendor2 = root['cfdi:Emisor']
        else:
            vendor = root['cfdi:Emisor']
            vendor2 = root['cfdi:Receptor']
        partner['rfc'] = vendor.get('@Rfc') or vendor.get('@rfc')
        invoice['rfc'] = vendor.get('@Rfc') or vendor.get('@rfc')
        invoice['company_rfc'] = vendor2.get('@Rfc') or vendor2.get('@rfc')
        partner['name'] = vendor.get('@Nombre', False) or vendor.get('@nombre', 'PARTNER GENERICO: REVISAR')
        partner['position_id'] = vendor.get('@RegimenFiscal')
        partner_rec = self.get_partner_or_create(partner)
        default_account = partner_rec.default_xml_import_account and partner_rec.default_xml_import_account.id or False
        partner_id = partner_rec.id
        if self.import_type == 'start_amount':
            if version == '3.3':
                invoice_line = self.compact_lines(root['cfdi:Conceptos']['cfdi:Concepto'], default_account)
            else:
                taxes = self.get_cfdi32_taxes(root['cfdi:Impuestos'])
                invoice_line = self.get_cfdi32(root['cfdi:Conceptos']['cfdi:Concepto'], taxes, default_account)
        else:
            invoice_line = self.add_products_to_invoice(root['cfdi:Conceptos']['cfdi:Concepto'], default_account)
        tipo_comprobante = root.get('@TipoDeComprobante') or root.get('@tipoDeComprobante')
        invoice['tipo_comprobante'] = tipo_comprobante
        corrected_invoice_type = False
        if tipo_comprobante.upper() == 'E':
            if self.invoice_type == 'out_invoice':
                corrected_invoice_type = 'out_refund'
            else:
                corrected_invoice_type = 'in_refund'
        moneda = root.get('@Moneda') or root.get('@moneda') or 'MXN'
        if moneda.upper() in ('M.N.', 'XXX', 'PESO MEXICANO'):
            moneda = 'MXN'
        currency = self.env['res.currency'].search([('name', '=', moneda)])
        folio = root.get('@Folio') or root.get('@folio')
        invoice['type'] = corrected_invoice_type or self.invoice_type
        invoice['name'] = folio
        invoice['amount_untaxed'] = root.get('@SubTotal') or root.get('@subTotal')
        invoice['amount_total'] = root.get('@Total') or root.get('@total')
        invoice['partner_id'] = partner_id
        invoice['currency_id'] = currency.id
        invoice['date_invoice'] = root.get('@Fecha') or root.get('@fecha')
        invoice['l10n_mx_edi_cfdi_name'] = filename
        invoice['journal_id'] = self.journal_id and self.journal_id.id or False
        invoice['team_id'] = self.team_id and self.team_id.id or False
        invoice['user_id'] = self.user_id and self.user_id.id or False
        invoice['account_id'] = self.invoice_account_id.id
        uuid = root['cfdi:Complemento']['tfd:TimbreFiscalDigital'].get('@UUID')
        invoice['uuid'] = uuid
        invoice['fiscal_position_id'] = partner_rec.property_account_position_id and partner_rec.property_account_position_id.id or False
        return (
         invoice, invoice_line, version)

    def get_cfdi32_taxes(self, taxes):
        tax_group = ''
        if taxes:
            if float(taxes.get('@totalImpuestosTrasladados', 0)) > 0:
                if type(taxes.get('cfdi:Traslados').get('cfdi:Traslado')) == list:
                    for item in taxes.get('cfdi:Traslados').get('cfdi:Traslado'):
                        tax_code = item.get('@impuesto')
                        tax_rate = item.get('@tasa')
                        if tax_code and tax_rate:
                            tax_group = tax_group + tax_code + '|' + tax_rate + '|tras,'

                else:
                    tax_code = taxes['cfdi:Traslados'].get('cfdi:Traslado').get('@impuesto')
                    tax_rate = taxes['cfdi:Traslados'].get('cfdi:Traslado').get('@tasa')
                if tax_code:
                    if tax_rate:
                        tax_group = tax_group + tax_code + '|' + tax_rate + '|tras,'
        return tax_group

    def get_cfdi32(self, products, taxes, default_account):
        if not isinstance(products, list):
            products = [
             products]
        all_products = []
        amount = 0
        for product in products:
            amount += float(product.get('@importe', 0)) - float(product.get('@descuento', 0))

        taxes = self.get_tax_ids(taxes, '3.2')
        invoice_line = {}
        invoice_line['name'] = 'SALDOS INICIALES'
        invoice_line['quantity'] = 1
        analytic_tag_ids = False
        if self.line_analytic_tag_ids:
            analytic_tag_ids = [
             (
              6, None, self.line_analytic_tag_ids.ids)]
        invoice_line['analytic_tag_ids'] = analytic_tag_ids
        invoice_line['account_analytic_id'] = self.line_analytic_account_id and self.line_analytic_account_id.id or False
        invoice_line['account_id'] = default_account or self.line_account_id.id
        invoice_line['price_subtotal'] = amount
        invoice_line['price_unit'] = amount
        invoice_line['taxes'] = taxes
        all_products.append(invoice_line)
        return [invoice_line]

    def compact_lines(self, products, default_account):
        """
          Rebisa las lienas de factura en el xml.
          y crea una sola linea por impuesto
        """
        all_products = []
        if not isinstance(products, list):
            products = [
             products]
        tax_groups = {}
        for product in products:
            tax_group = ''
            check_taxes = product.get('cfdi:Impuestos')
            if check_taxes:
                taxes = check_taxes.get('cfdi:Traslados')
                if taxes:
                    if type(taxes.get('cfdi:Traslado')) == list:
                        for item in taxes.get('cfdi:Traslado'):
                            tax_code = item.get('@Impuesto', '')
                            tax_rate = item.get('@TasaOCuota', '0')
                            tax_factor = item.get('@TipoFactor', '')
                            if tax_code:
                                tax_group = tax_group + tax_code + '|' + tax_rate + '|tras|' + tax_factor + ','

                    else:
                        tax_code = taxes.get('cfdi:Traslado').get('@Impuesto', '')
                        tax_rate = taxes.get('cfdi:Traslado').get('@TasaOCuota', '0')
                        tax_factor = taxes.get('cfdi:Traslado').get('@TipoFactor', '')
                        if tax_code:
                            tax_group = tax_group + tax_code + '|' + tax_rate + '|tras|' + tax_factor + ','
                taxes = check_taxes.get('cfdi:Retenciones')
                if taxes:
                    if type(taxes.get('cfdi:Retencion')) == list:
                        for item in taxes.get('cfdi:Retencion'):
                            tax_code = item.get('@Impuesto', '')
                            tax_rate = item.get('@TasaOCuota', '0')
                            tax_factor = item.get('@TipoFactor', '')
                            if tax_code:
                                tax_group = tax_group + tax_code + '|' + tax_rate + '|ret|' + tax_factor + ','

                    else:
                        tax_code = taxes.get('cfdi:Retencion').get('@Impuesto')
                        tax_rate = taxes.get('cfdi:Retencion').get('@TasaOCuota')
                        tax_factor = taxes.get('cfdi:Retencion').get('@TipoFactor')
                    if tax_code:
                        tax_group = tax_group + tax_code + '|' + tax_rate + '|ret|' + tax_factor + ','
            if tax_group in tax_groups:
                tax_groups[tax_group]['price_subtotal'] += float(product['@Importe']) - float(product.get('@Descuento', 0.0))
            else:
                tax_groups[tax_group] = {}
                tax_groups[tax_group]['price_subtotal'] = float(product['@Importe']) - float(product.get('@Descuento', 0.0))

        for group in tax_groups:
            taxes = self.get_tax_ids(group)
            invoice_line = {}
            invoice_line['name'] = 'SALDOS INICIALES'
            invoice_line['quantity'] = 1
            analytic_tag_ids = False
            if self.line_analytic_tag_ids:
                analytic_tag_ids = [
                 (
                  6, None, self.line_analytic_tag_ids.ids)]
            invoice_line['analytic_tag_ids'] = analytic_tag_ids
            invoice_line['account_analytic_id'] = self.line_analytic_account_id and self.line_analytic_account_id.id or False
            invoice_line['account_id'] = default_account or self.line_account_id.id
            invoice_line['price_subtotal'] = tax_groups[group]['price_subtotal']
            invoice_line['price_unit'] = tax_groups[group]['price_subtotal']
            invoice_line['taxes'] = taxes
            all_products.append(invoice_line)

        return all_products

    def add_products_to_invoice(self, products, default_account):
        """
            Obtener datos de los productos (Conceptos).
        """
        all_products = []
        if not isinstance(products, list):
            products = [
             products]
        for product in products:
            invoice_line = {}
            invoice_line['name'] = product.get('@Descripcion') or product.get('@descripcion')
            invoice_line['quantity'] = product.get('@Cantidad') or product.get('@cantidad')
            invoice_line['price_subtotal'] = product.get('@Importe') or product.get('@importe')
            invoice_line['price_unit'] = product.get('@ValorUnitario') or product.get('@valorUnitario')
            invoice_line['sat_product_ref'] = product.get('@ClaveProdServ') or product.get('@claveProdServ')
            invoice_line['product_ref'] = product.get('@NoIdentificacion') or product.get('@noIdentificacion')
            invoice_line['sat_uom'] = product.get('@ClaveUnidad') or product.get('@claveUnidad')
            analytic_tag_ids = False
            if self.line_analytic_tag_ids:
                analytic_tag_ids = [
                 (
                  6, None, self.line_analytic_tag_ids.ids)]
            invoice_line['analytic_tag_ids'] = analytic_tag_ids
            invoice_line['account_analytic_id'] = self.line_analytic_account_id and self.line_analytic_account_id.id or False
            invoice_line['account_id'] = default_account or self.line_account_id.id
            if product.get('@Descuento'):
                invoice_line['discount'] = self.get_discount_percentage(product)
            else:
                invoice_line['discount'] = 0.0
             
            line_product_id = self.get_product_or_create(invoice_line)
            invoice_line['product_id'] = line_product_id
            if not line_product_id:
                product_name = product.get('@Descripcion') or product.get('@descripcion')
                clave_sat = product.get('@ClaveProdServ') or product.get('@claveProdServ')
                invoice_line['name'] = '['+clave_sat+'] '+product_name

            tax_group = ''
            check_taxes = product.get('cfdi:Impuestos')
            if check_taxes:
                invoice_taxes = []
                if check_taxes.get('cfdi:Traslados'):
                    traslado = {}
                    t = check_taxes['cfdi:Traslados']['cfdi:Traslado']
                    if not isinstance(t, list):
                        t = [
                         t]
                    for element in t:
                        tax_code = element.get('@Impuesto', '')
                        tax_rate = element.get('@TasaOCuota', '0')
                        tax_factor = element.get('@TipoFactor', '')
                        tax_group = tax_group + tax_code + '|' + tax_rate + '|tras|' + tax_factor + ','

                if check_taxes.get('cfdi:Retenciones'):
                    retencion = {}
                    r = check_taxes['cfdi:Retenciones']['cfdi:Retencion']
                    if not isinstance(r, list):
                        r = [
                         r]
                    for element in r:
                        tax_code = element.get('@Impuesto', '')
                        tax_rate = element.get('@TasaOCuota', '0')
                        tax_factor = element.get('@TipoFactor', '')
                        tax_group = tax_group + tax_code + '|' + tax_rate + '|ret|' + tax_factor + ','

                taxes = False
                if tax_group:
                    taxes = self.get_tax_ids(tax_group)
                invoice_line['taxes'] = taxes
            all_products.append(invoice_line)

        return all_products

    def create_bill_draft(self, invoice, invoice_line, uuid_name=False):
        """
            Toma la factura y sus conceptos y los guarda
            en Odoo como borrador.
        """
        vals = {
            #'l10n_mx_edi_cfdi_name':invoice['l10n_mx_edi_cfdi_name'], 
            'l10n_mx_edi_cfdi_name2': uuid_name if uuid_name else invoice['l10n_mx_edi_cfdi_name'], 
            'journal_id': invoice['journal_id'], 
            'team_id'   : invoice['team_id'], 
            'is_imported': True,
            'user_id'   : invoice['user_id'] or self.env.user.id, 
            #'account_id':invoice['account_id'], 
            'invoice_date' : invoice['date_invoice'], 
            'partner_id':invoice['partner_id'], 
            #'amount_untaxed':invoice['amount_untaxed'], 
            #'amount_total':invoice['amount_total'], 
            'currency_id':invoice['currency_id'], 
            'move_type':invoice['type'], 
            'is_start_amount':True if self.import_type == 'start_amount' else False
        }
        #if self.invoice_type == 'out_invoice' or self.invoice_type == 'out_refund':
        #    vals['name'] = invoice['name']
        #else:
        vals['ref'] = invoice['name']
        
        lines = []
        for line in invoice_line:
            uom = False
            if self.import_type != 'start_amount':
                uom = self.get_uom(line.get('sat_uom'))
                if uom:
                    uom = uom.id
                else:
                    uom = False
            line_data = {
                'product_id' : line.get('product_id'), 
                'name'       : line['name'], 
                'quantity'   : line['quantity'], 
                'price_unit' : line['price_unit'], 
                'account_id' : line['account_id'], 
                'discount'   : line.get('discount') or 0.0, 
                #'price_subtotal' : line['price_subtotal'], 
                'tax_ids' : line.get('taxes'), 
                'product_uom_id'    : uom, 
                'analytic_tag_ids' : line['analytic_tag_ids'], 
                'analytic_account_id' : line['account_analytic_id']
            }
            
            lines.append((0,0,line_data))
        vals['invoice_line_ids'] = lines
        draft = self.env['account.move'].create(vals)
        
        return draft

    def get_payment_term_line(self, days):
        """
        obtiene linea de termino de pago indicado,
        se podra accedfer al termino de pago desde el campo payment_id
        days: in que representa el no. de dias del t. de pago a buscar
        """
        payment_term_line_id = False
        PaymentTermLine = self.env['account.payment.term.line']
        domain = [('days', '=', days), ('payment_id.company_id', '=', self.company_id.id)]
        payment_term_line_id = PaymentTermLine.search(domain)
        if payment_term_line_id:
            payment_term_line_id = payment_term_line_id[0]
        return payment_term_line_id

    def get_partner_or_create(self, partner):
        """Obtener ID de un partner (proveedor). Si no existe, lo crea."""
        search_domain = [
         (
          'vat', '=', partner['rfc'])]
        if self.invoice_type == 'out_invoice' or self.invoice_type == 'out_refund':
            search_domain.append(('customer_rank', '!=', 0))
        else:
            search_domain.append(('supplier_rank', '!=', 0))
        p = self.env['res.partner'].search(search_domain, limit=1)
        create_generic = False
        if partner['rfc'] in ('XEXX010101000', 'XAXX010101000'):
            for partner_rec in p:
                if partner_rec.name == partner['name']:
                    p = [partner_rec]
                    break
            else:
                create_generic = True

        else:
            payment_term_id = False
            if not p or create_generic:
                if self.payment_term_id:
                    payment_term_id = self.payment_term_id
                else:
                    payment_term_line_id = self.get_payment_term_line(15)
                    if payment_term_line_id:
                        payment_term_id = payment_term_line_id.payment_id
                    #fiscal_position_code = partner.get('position_id')
                    #fiscal_position = self.env['account.fiscal.position'].search([
                    # (
                    #  'l10n_mx_edi_code', '=', fiscal_position_code)])
                    #fiscal_position = fiscal_position and fiscal_position[0]
                    #fiscal_position_id = fiscal_position.id or False
                payment_term_id = self.payment_term_id
                vals = {
                    'name'  : partner['name'], 
                    'vat'   : partner['rfc'], 
                    #'property_account_position_id':fiscal_position_id
                }
                if self.invoice_type == 'out_invoice' or self.invoice_type == 'out_refund':
                    vals['property_payment_term_id'] = payment_term_id and payment_term_id.id or False
                    vals['customer_rank'] = True
                    vals['supplier_rank'] = 1
                else:
                    vals['property_supplier_payment_term_id'] = payment_term_id and payment_term_id.id or False
                    vals['customer_rank'] = False
                    vals['supplier_rank'] = 2
                country = self.env['res.country'].search([('code','=','MX')], limit=1)
                vals['country_id'] = country.id
                p = self.env['res.partner'].create(vals)
            else:
                p = p[0]
        return p

    def get_uom(self, sat_code):
        """
        obtiene record de unidad de medida
        sat_code: string con el codigo del sat de la unidad de medida
        """
        ProductUom = self.env['uom.uom']
        return ProductUom.search([('unspsc_code_id.code', '=', sat_code)], limit=1)

    def get_product_or_create(self, product):
        """Obtener ID de un producto. Si no existe, lo crea."""
        product_ref = product.get('product_ref', False)
        sat_product_ref = product.get('sat_product_ref', False)
        p = self.env['product.product'].search([
         (
          'name', '=', product['name'])])
        p = p[0] if p else False
        if not p:
            # niq_pos_multi_barcodes

            if self.search_by == 'default_code':
                if product_ref:
                    p = self.env['product.product'].search([
                     ('default_code', '=', product_ref)], limit=1)
                    if p:
                        return p.id
                if self.create_product:
                    EdiCode = self.env['product.unspsc.code']
                    product_vals = {
                        'name'  : product['name'],
                        'price' : product['price_unit'], 
                        'default_code' : product['product_ref'], 
                        'detailed_type':'product'}
                    sat_code = EdiCode.search([('applies_to','=','product'),
                                               ('code', '=', product['sat_product_ref'])], limit=1)
                    if sat_code:
                        product_vals['unspsc_code_id'] = sat_code.id
                    uom = self.get_uom(product['sat_uom'])
                    if uom:
                        product_vals['uom_id'] = uom.id
                        product_vals['uom_po_id'] = uom.id
                    p = self.env['product.product'].create(product_vals)
                    return p.id or False
                return False
            else:
                EdiCode = self.env['product.unspsc.code']
                edi_sat_code_id = EdiCode.search([('code', '=', product['sat_product_ref'])], limit=1)
                if edi_sat_code_id:
                    p = self.env['product.product'].search([
                     ('unspsc_code_id', '=', edi_sat_code_id.id)], limit=1)
                    if p:
                        return p.id
                    else:
                        p = self.env['product.template.unspsc.multi'].search([
                            ('unspsc_code_id', '=', edi_sat_code_id.id)], limit=1)
                        if p:
                            return p.product_template_id.product_variant_id.id
                return False        
        else:
            return p.id

    def add_product_tax(self, invoice_id, vals):
        """Agregar impuestos correspondientes a una factura y sus conceptos."""
        for tax in vals['taxes']:
            tax_id = tax['tax_id'][1]
            if tax_id == 6:
                pass
            else:
                tax_name = self.env['account.tax'].search([('id', '=', tax_id)]).name
                self.env['account.move.tax'].create({'invoice_id':invoice_id, 
                 'name':tax_name, 
                 'tax_id':tax_id, 
                 'account_id':tax['account_id'], 
                 'amount':tax['amount'], 
                 'base':tax['base']})

    def get_discount_percentage(self, product):
        """Calcular descuento de un producto en porcentaje."""
        d = float(product['@Descuento']) / float(product['@Importe']) * 100
        return d

    def show_validation_results_to_user(self, bills):
        """
            Checar si los XMLs subidos son válidos.
            Mostrar error al usuario si no, y detener proceso.
        """
        if any(d['valid'] == False for d in bills):
            not_valid = [bill for bill in bills if not bill.get('valid')]
            msg = 'Los siguientes archivos no son válidos:\n'
            for bill in not_valid:
                msg += str(bill.get('filename', '')) + ' - ' + str(bill.get('state', '')) + '\n'

            raise ValidationError(msg)
        else:
            return True
# okay decompiling xml_import.pyc
