
# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _, tools
from odoo.tools import float_is_zero, float_compare, pycompat
from odoo.tools.misc import formatLang
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo.addons import decimal_precision as dp

import base64
from lxml.objectify import fromstring
import json, re, uuid
from functools import partial
from lxml import etree
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_encode
import logging
_logger = logging.getLogger(__name__)

CFDI_XSLT_CADENA = 'l10n_mx_edi/data/3.3/cadenaoriginal.xslt'
CFDI_XSLT_CADENA_TFD = 'l10n_mx_edi/data/xslt/3.3/cadenaoriginal_TFD_1_1.xslt'


class AccountMove(models.Model):
    _inherit = 'account.move'
    l10n_mx_edi_cfdi_name2 = fields.Char(copy=False)
    is_start_amount = fields.Boolean('Es saldo inicial', help='Si es True, esta factura es de saldos inciiales')
    is_imported = fields.Boolean('Es Importada',
                                 help="Si está marcado significa que la Factura fue importada")
    
    def action_post(self):
        res = super(AccountMove, self).action_post()
        for rec in self:
            if not rec.is_imported:
                continue
            doc = rec.edi_document_ids.filtered(lambda w: w.edi_format_id.code=='cfdi_3_3' and w.state=='to_send')
            if not doc:
                continue
            doc.write({
                'attachment_id' : rec.attachment_ids.filtered(lambda ww: ww.name.endswith('xml'))[0].id,
                'state' : 'sent',                   
            })            
        return res
    
    
    
    def _l10n_mx_edi_decode_cfdi(self, cfdi_data=None):
        ''' Helper to extract relevant data from the CFDI to be used, for example, when printing the invoice.
        :param cfdi_data:   The optional cfdi data.
        :return:            A python dictionary.
        '''
        self.ensure_one()

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

        # Find a signed cfdi.
        if not cfdi_data:
            if self.is_imported:
                try:
                    cfdi_data = base64.decodebytes(self.attachment_ids.filtered(lambda x: x.name.endswith('xml'))[0])
                except:
                    pass
            if not cfdi_data:
                signed_edi = self._get_l10n_mx_edi_signed_edi_document()
                if signed_edi:
                    cfdi_data = base64.decodebytes(signed_edi.attachment_id.with_context(bin_size=False).datas)
                
        # Nothing to decode.
        if not cfdi_data:
            return {}
        cfdi_node = fromstring(cfdi_data)
        tfd_node = get_node(
            cfdi_node,
            'tfd:TimbreFiscalDigital[1]',
            {'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'},
        )

        return {
            'uuid': ({} if tfd_node is None else tfd_node).get('UUID'),
            'supplier_rfc': cfdi_node.Emisor.get('Rfc', cfdi_node.Emisor.get('rfc')),
            'customer_rfc': cfdi_node.Receptor.get('Rfc', cfdi_node.Receptor.get('rfc')),
            'amount_total': cfdi_node.get('Total', cfdi_node.get('total')),
            'cfdi_node': cfdi_node,
            'usage': cfdi_node.Receptor.get('UsoCFDI'),
            'payment_method': cfdi_node.get('formaDePago', cfdi_node.get('MetodoPago')),
            'bank_account': cfdi_node.get('NumCtaPago'),
            'sello': cfdi_node.get('sello', cfdi_node.get('Sello', 'No identificado')),
            'sello_sat': tfd_node is not None and tfd_node.get('selloSAT', tfd_node.get('SelloSAT', 'No identificado')),
            'cadena': get_cadena(cfdi_node, CFDI_XSLT_CADENA),
            'certificate_number': cfdi_node.get('noCertificado', cfdi_node.get('NoCertificado')),
            'certificate_sat_number': tfd_node is not None and tfd_node.get('NoCertificadoSAT'),
            'expedition': cfdi_node.get('LugarExpedicion'),
            'fiscal_regime': cfdi_node.Emisor.get('RegimenFiscal', ''),
            'emission_date_str': cfdi_node.get('fecha', cfdi_node.get('Fecha', '')).replace('T', ' '),
            'stamp_date': tfd_node is not None and tfd_node.get('FechaTimbrado', '').replace('T', ' '),
        }
    
    def action_invoice_open(self):
        res = super(AccountMove, self).action_invoice_open()
        for rec in self:
            if rec.l10n_mx_edi_cfdi_name2:
                rec.l10n_mx_edi_cfdi_name = rec.l10n_mx_edi_cfdi_name2

        return res

    
    def action_move_create(self):
        res = super(AccountMove, self).action_move_create()
        for inv in self:
            if inv.l10n_mx_edi_cfdi_name2:
                if inv.move_type == 'out_invoice' or inv.move_type == 'out_refund':
                    inv.move_id.name = inv.name
                elif (inv.move_type == 'in_invoice' or inv.move_type == 'in_refund') and inv.is_start_amount:
                    inv.move_id.name = inv.reference

        return res


class AccountTax(models.Model):
    _inherit = 'account.tax'
    tax_code_mx = fields.Char(string='Codigo cuenta')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    codes_unspsc_multi_ids = fields.One2many('product.template.unspsc.multi', 'product_template_id', 'Codigos UNSPSC Asociados')

# class ProductTemplate(models.Model):
#     _inherit = 'product.product'

#     codes_unspsc_multi_ids = fields.One2many('product.template.unspsc.multi', 'product_template_id', 'Codigos UNSPSC Asociados')


class ProductTemplateUnspscMulti(models.Model):
    _name = 'product.template.unspsc.multi'
    _description = 'Relacion Multiple Codigos UNSPSC'
    _rec_name = 'unspsc_code_id' 

    unspsc_code_id = fields.Many2one('product.unspsc.code', 'Categoría de producto UNSPSC', domain=[('applies_to', '=', 'product')],
        help='The UNSPSC code related to this product.  Used for edi in Colombia, Peru and Mexico')

    product_template_id = fields.Many2one('product.template', 'ID Ref. UNSPSC MUlti')
