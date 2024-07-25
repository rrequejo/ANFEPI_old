from odoo import models, fields, api # type: ignore

class InvoiceWizard(models.TransientModel):
    _name = 'invoice.wizard'
    _description = 'Invoice Selection Wizard'

    invoice_id = fields.Many2one('account.move', string='Invoice')

    def action_select_invoice(self):
        active_id = self.env.context.get('active_id')
        print(active_id)
        downloaded_xml = self.env['account.edi.downloaded.xml.sat'].search([('id','=',active_id)],limit=1)
        self.invoice_id.xml_imported_id = downloaded_xml.id
        downloaded_xml.state = self.invoice_id.state
        downloaded_xml.imported = True
        downloaded_xml.invoice_id = self.invoice_id.id
        return {'type': 'ir.actions.act_window_close'}