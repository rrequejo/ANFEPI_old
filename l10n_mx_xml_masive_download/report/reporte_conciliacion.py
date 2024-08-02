from odoo import fields, models, tools, api
from datetime import date

class ReporteConciliacion(models.Model):
    _name = 'sat.conciliation.report'
    _description = "Reporte de conciliacion sat vs odoo"
 
    document_type = fields.Selection([
        ('I', 'Ingreso'),
        ('E', 'Egreso'),
        ('T', 'Traslado'),
        ('N', 'Nomina'),
        ('P', 'Pago'),
    ], string='Tipo de Documento')
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
        self.search([]).unlink()  

        # Fetch SAT DATA

        sat_records = self.env['account.edi.downloaded.xml.sat'].search([
            ('document_date', '>=', start_date),
            ('document_date', '<=', end_date),
            #('cfdi_type','=','emitidos')
        ])

        grouped_sat_data = {}
        for item in sat_records:
            doc_type = item["document_type"]
            if doc_type not in grouped_sat_data:
                grouped_sat_data[doc_type] = []
            grouped_sat_data[doc_type].append({'total_amount':item.amount_total})

        # Fetch Odoo Data

        odoo_records_I = self.env['account.move'].search([
            ('invoice_date', '>=', start_date),
            ('invoice_date', '<=', end_date),
            ('move_type','=','in_invoice')
        ])

        odoo_records_E = self.env['account.move'].search([
            ('invoice_date', '>=', start_date),
            ('invoice_date', '<=', end_date),
            ('move_type','=','out_invoice')
        ])
        
        odoo_records_P = self.env['account.payment'].search([
            ('date', '>=', start_date),
            ('date', '<=', end_date),
        ])

        print("Odoo Records: "+str(len(odoo_records_I)))

        report_model = self.env['sat.conciliation.report']

        for doc_type, items in grouped_sat_data.items():
            total_sat_items = 0
            total_sat_amount = 0
            total_odoo_items = 0
            total_odoo_amount = 0
            for item in items:
                total_sat_items += 1
                total_sat_amount += item['total_amount']

            if doc_type == 'I':
                for item in odoo_records_I:
                    total_odoo_amount += item.amount_total_signed
                    total_odoo_items += 1

            if doc_type == 'E':
                for item in odoo_records_E:
                    total_odoo_amount += item.amount_total_signed
                    total_odoo_items += 1

            if doc_type == 'P':
                for item in odoo_records_P:
                    total_odoo_amount += item.amount_company_currency_signed
                    total_odoo_items += 1

            report_model.create({
                'document_type': doc_type,
                'total_odoo': total_odoo_items,
                'total_sat': total_sat_items,
                'diferencia_uuid': total_odoo_items - total_sat_items,
                'diferencia_importe': total_odoo_amount - total_sat_amount
            })



        action = self.env.ref('l10n_mx_xml_masive_download.account_edi_download_conciliation_report_action')
        return {
                'type': 'ir.actions.act_window',
                'name': action.name,
                'res_model': action.res_model,
                'view_mode': 'pivot',
                'view_id': action.view_id.id,
                'target': 'current',
            }
