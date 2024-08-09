from odoo import fields, models, tools, api
from datetime import date

class ReporteConciliacion(models.Model):
    _name = 'sat.conciliation.report'
    _description = "Reporte de conciliacion sat vs odoo"
 
    document_type = fields.Char(string='Tipo de Documento')
    total_odoo = fields.Integer(string="Total de UUID en el sistema")
    total_sat = fields.Integer(string="Total de UUID en el SAT")
    diferencia_uuid = fields.Integer(string="Diferencia de UUID's")
    diferencia_importe = fields.Integer(string="Diferencia de Importes")
    start_date = fields.Date(string='Start Date', default=lambda self: date(date.today().year, 1, 1))
    end_date = fields.Date(string='End Date', default=fields.Date.today)

    def generateReport(self, start_date, end_date):
        if not start_date:
            start_date = date(date.today().year, 1, 1)
        if not end_date:
            end_date = date.today()   

        # Erase previous report 
        report = []
        self.search([]).unlink()  
        report_model = self.env['sat.conciliation.report']

        # =======================================================================
        #
        # 1. Facturas de Cliente Emitidas de Ingreso
        #
        # =======================================================================

        in_odoo = self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('move_type','=','out_invoice'),
            ('l10n_mx_edi_cfdi_sat_state','=','valid'),
            ('invoice_date','>=',start_date),
            ('invoice_date','<=',end_date),
        ])

        in_sat = self.env['account.edi.downloaded.xml.sat'].search([
            ('cfdi_type','=','emitidos'),
            ('state','!=','ignored'),
            ('document_type','=','I'),
            ('document_date','>=',start_date),
            ('document_date','<=',end_date),
        ])

        in_odoo_sum = sum(in_odoo.mapped('amount_total_signed'))
        in_sat_sum = sum(in_sat.mapped('amount_total'))
        
        report.append({
            'document_type':"Facturas Cliente: Emitidas",
            'total_odoo':len(in_odoo),
            'total_sat':len(in_sat),
            'diferencia_uuid':len(in_odoo) - len(in_sat),
            'diferencia_importe':in_odoo_sum - in_sat_sum,
        })

        # =======================================================================
        #
        # 2. Notas de Credito: Emitidas de Egreso
        #
        # =======================================================================

        in_odoo = self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('move_type','=','out_refund'),
            ('l10n_mx_edi_cfdi_sat_state','=','valid'),
            ('invoice_date','>=',start_date),
            ('invoice_date','<=',end_date),
        ])

        in_sat = self.env['account.edi.downloaded.xml.sat'].search([
            ('cfdi_type','=','emitidos'),
            ('state','!=','ignored'),
            ('document_type','=','E'),
            ('document_date','>=',start_date),
            ('document_date','<=',end_date),
        ])

        in_odoo_sum = sum(in_odoo.mapped('amount_total_signed'))
        in_sat_sum = sum(in_sat.mapped('amount_total'))
        
        report.append({
            'document_type':"Notas de Credito: Emitidas",
            'total_odoo':len(in_odoo),
            'total_sat':len(in_sat),
            'diferencia_uuid':len(in_odoo) - len(in_sat),
            'diferencia_importe':in_odoo_sum - in_sat_sum,
        })

        # =======================================================================
        #
        # 3. Facturas de Proveedor Recibidas de Ingreso
        #
        # =======================================================================

        in_odoo = self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('move_type','=','in_invoice'),
            ('l10n_mx_edi_cfdi_sat_state','=','valid'),
            ('invoice_date','>=',start_date),
            ('invoice_date','<=',end_date),
        ])

        in_sat = self.env['account.edi.downloaded.xml.sat'].search([
            ('cfdi_type','=','recibidos'),
            ('state','!=','ignored'),
            ('document_type','=','I'),
            ('document_date','>=',start_date),
            ('document_date','<=',end_date),
        ])

        in_odoo_sum = sum(in_odoo.mapped('amount_total_signed'))
        in_sat_sum = sum(in_sat.mapped('amount_total'))
        
        report.append({
            'document_type':"Facturas de Proveedor: Recibidas",
            'total_odoo':len(in_odoo),
            'total_sat':len(in_sat),
            'diferencia_uuid':len(in_odoo) - len(in_sat),
            'diferencia_importe':in_odoo_sum - in_sat_sum,
        })

        # =======================================================================
        #
        # 4. Notas de Credito: Emitidas de Egreso
        #
        # =======================================================================

        in_odoo = self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('move_type','=','in_refund'),
            ('l10n_mx_edi_cfdi_sat_state','=','valid'),
            ('invoice_date','>=',start_date),
            ('invoice_date','<=',end_date),
        ])

        in_sat = self.env['account.edi.downloaded.xml.sat'].search([
            ('cfdi_type','=','recibidos'),
            ('state','!=','ignored'),
            ('document_type','=','E'),
            ('document_date','>=',start_date),
            ('document_date','<=',end_date),
        ])

        in_odoo_sum = sum(in_odoo.mapped('amount_total_signed'))
        in_sat_sum = sum(in_sat.mapped('amount_total'))
        
        report.append({
            'document_type':"Notas de Credito Proveedor: Recibidas",
            'total_odoo':len(in_odoo),
            'total_sat':len(in_sat),
            'diferencia_uuid':len(in_odoo) - len(in_sat),
            'diferencia_importe':in_odoo_sum - in_sat_sum,
        })
        
        # =======================================================================
        #
        # 5. Complemento de Pago Emitidos
        #
        # =======================================================================

        in_odoo = self.env['account.payment'].search([
            ('state', '=', 'posted'),
            ('payment_type','=','outbound'),
            ('date','>=',start_date),
            ('date','<=',end_date),
        ])

        in_sat = self.env['account.edi.downloaded.xml.sat'].search([
            ('cfdi_type','=','emitidos'),
            ('state','!=','ignored'),
            ('document_type','=','P'),
            ('document_date','>=',start_date),
            ('document_date','<=',end_date),
        ])

        in_odoo_sum = sum(in_odoo.mapped('amount_company_currency_signed'))
        in_sat_sum = sum(in_sat.mapped('amount_total'))

        report.append({
            'document_type':"Complemento de Pago Emitidos",
            'total_odoo':len(in_odoo),
            'total_sat':len(in_sat),
            'diferencia_uuid':len(in_odoo) - len(in_sat),
            'diferencia_importe':in_odoo_sum - in_sat_sum,
        })
          

        # =======================================================================
        #
        # 6. Complemento de Pago Recibidos
        #
        # =======================================================================

        in_odoo = self.env['account.payment'].search([
            ('state', '=', 'posted'),
            ('payment_type','=','inbound'),
            ('date','>=',start_date),
            ('date','<=',end_date),
        ])

        in_sat = self.env['account.edi.downloaded.xml.sat'].search([
            ('cfdi_type','=','recibidos'),
            ('state','!=','ignored'),
            ('document_type','=','P'),
            ('document_date','>=',start_date),
            ('document_date','<=',end_date),
        ])

        in_odoo_sum = sum(in_odoo.mapped('amount_company_currency_signed'))
        in_sat_sum = sum(in_sat.mapped('amount_total'))

        report.append({
            'document_type':"Complemento de Pago Recibidos",
            'total_odoo':len(in_odoo),
            'total_sat':len(in_sat),
            'diferencia_uuid':len(in_odoo) - len(in_sat),
            'diferencia_importe':in_odoo_sum - in_sat_sum,
        })

        report_model.create(report)

        action = self.env.ref('l10n_mx_xml_masive_download.account_edi_download_conciliation_report_action')
        return {
                'type': 'ir.actions.act_window',
                'name': action.name,
                'res_model': action.res_model,
                'view_mode': 'pivot',
                'view_id': action.view_id.id,
                'target': 'current',
            }