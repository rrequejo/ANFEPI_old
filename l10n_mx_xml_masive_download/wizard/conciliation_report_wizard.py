from odoo import models, fields, api # type: ignore

class ConsiliationReportWizard(models.TransientModel):
    _name = 'conciliation.report.wizard'
    _description = 'Invoice Selection Wizard'

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    def action_launch_report(self):
        return self.env['sat.conciliation.report'].generateReport(self.start_date, self.end_date)