# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
import time
import base64
import requests 
import logging
from lxml import etree
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    def validate_attachments_xml(self, res_model='', res_id='', data='', args=''):
        print ("############ validate_attachments_xml ............ ")
        print ("############ res_model: ", res_model)
        print ("############ res_id: ", res_id)
        print("########### DATA: "+str(base64.b64decode(data['data'])))

        cfdi_decoded = self.env['l10n_mx_edi.document']._decode_cfdi_attachment(base64.b64decode(data['data']))
        print(cfdi_decoded)
        existing_uuid = self.env['ir.attachment'].search([('cfdi_uuid','=',cfdi_decoded.get('uuid'))])
        if existing_uuid:
            raise UserError("Ya existe un XML con el mismo UUID en el sistema")
            # Validate sat state
        else:
            sat_status = self._fetch_sat_status(
                cfdi_decoded.get('supplier_rfc'), 
                cfdi_decoded.get('customer_rfc'),  
                cfdi_decoded.get('amount_total'), 
                cfdi_decoded.get('uuid')
            )
            if sat_status != 'Vigente':
                raise UserError("El estado del CFDI no fue validado ante el SAT, vuelva a intentar en unos minutos")
        if res_model != 'account.move':
            _logger.info("\n #### No se valida cualquier otro modelo que no sea account.move ...............")
            return True
        return True, data

    def _fetch_sat_status(self, supplier_rfc, customer_rfc, total, uuid):
        url = 'https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc?wsdl'
        headers = {
            'SOAPAction': 'http://tempuri.org/IConsultaCFDIService/Consulta',
            'Content-Type': 'text/xml; charset=utf-8',
        }
        params = f'<![CDATA[?id={uuid or ""}' \
                 f'&re={tools.html_escape(supplier_rfc or "")}' \
                 f'&rr={tools.html_escape(customer_rfc or "")}' \
                 f'&tt={total or 0.0}]]>'
        envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
            <SOAP-ENV:Envelope
                xmlns:ns0="http://tempuri.org/"
                xmlns:ns1="http://schemas.xmlsoap.org/soap/envelope/"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
                <SOAP-ENV:Header/>
                <ns1:Body>
                    <ns0:Consulta>
                        <ns0:expresionImpresa>{params}</ns0:expresionImpresa>
                    </ns0:Consulta>
                </ns1:Body>
            </SOAP-ENV:Envelope>
        """
        namespace = {'a': 'http://schemas.datacontract.org/2004/07/Sat.Cfdi.Negocio.ConsultaCfdi.Servicio'}

        try:
            soap_xml = requests.post(url, data=envelope, headers=headers, timeout=35)
            response = etree.fromstring(soap_xml.text)
            fetched_status = response.xpath('//a:Estado', namespaces=namespace)
            fetched_state = fetched_status[0].text if fetched_status else None
        except Exception as e:
            return {
                'error': _("Failure during update of the SAT status: %s", str(e)),
                'value': 'error',
            }
        if fetched_state == 'Vigente':
            return 'Vigente'
        elif fetched_state == 'Cancelado':
            return 'Cancelado'
        elif fetched_state == 'No Encontrado':
            return 'No Encontrado'
        else:
            return 'Sin Definir'
