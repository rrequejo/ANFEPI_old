from odoo import fields, models, tools


class ReporteConciliacion(models.Model):
    """ Model for generating pivot view for product variants based on product
     locations"""
    _name = 'sat.conciliation.report'
    _description = "Reporte de conciliacion sat vs odoo"
    _auto = False


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
    diferencia_importe = fields.Integer(string="Diferencia de UUID's")


    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'sat_conciliation_report')
        self.env.cr.execute("""
            CREATE VIEW sat_conciliation_report AS (
                SELECT
                    id,
                    document_type,
                    total_odoo,
                    total_sat,
                    diferencia_uuid,
                    diferencia_importe
                FROM (
                    SELECT
                        1 AS id,
                        'I' AS document_type,
                        100 AS total_odoo,
                        120 AS total_sat,
                        20 AS diferencia_uuid,
                        5000 AS diferencia_importe
                    UNION ALL
                    SELECT
                        2 AS id,
                        'I' AS document_type,
                        150 AS total_odoo,
                        140 AS total_sat,
                        -10 AS diferencia_uuid,
                        2000 AS diferencia_importe
                    UNION ALL
                    SELECT
                        3 AS id,
                        'T' AS document_type,
                        200 AS total_odoo,
                        180 AS total_sat,
                        -20 AS diferencia_uuid,
                        3000 AS diferencia_importe
                    UNION ALL
                    SELECT
                        4 AS id,
                        'N' AS document_type,
                        50 AS total_odoo,
                        55 AS total_sat,
                        5 AS diferencia_uuid,
                        1000 AS diferencia_importe
                    UNION ALL
                    SELECT
                        5 AS id,
                        'P' AS document_type,
                        75 AS total_odoo,
                        70 AS total_sat,
                        -5 AS diferencia_uuid,
                        1500 AS diferencia_importe
                ) AS data
            )
        """)