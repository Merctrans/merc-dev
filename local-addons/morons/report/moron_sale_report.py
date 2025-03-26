from odoo import models, fields, api
from odoo import tools


class MoronSaleReport(models.Model):
    _name = "moron.sale.report"
    _description = "Moron Sale Report"
    _auto = False

    project_id = fields.Many2one("project.project", string="Project")
    partner_id = fields.Many2one("res.partner", string="Customer")
    currency_usd_id = fields.Many2one('res.currency', "USD", readonly=True,
                                        compute="_compute_currency_usd_id")
    invoice_date = fields.Date("Invoice Date", readonly=True)
    # job_value_usd = fields.Monetary("Project Value (USD)", currency_field="currency_usd_id", readonly=True)

    # Customer
    moron_sale_order_id = fields.Many2one('moron.sale.order', string='Moron SO', readonly=True)
    client_invoice_id = fields.Many2one('account.move', string='Client Invoice', readonly=True)
    # Contributor
    moron_purchase_order_id = fields.Many2one('project.task', string='Moron PO', readonly=True)
    contributor_invoice_id = fields.Many2one('account.move', string='Contributor Invoice', readonly=True)

    # Amount
    # revenue: Tổng hợp số liệu từ Client Invoice
    # project_cost: Tổng hợp số liệu từ Contributor Invoice value
    # production_profit: revenue - project_cost
    # margin: (production_profit / revenue) * 100
    revenue = fields.Monetary("Revenue", currency_field="currency_usd_id", readonly=True)
    project_cost = fields.Monetary("Project Cost", currency_field="currency_usd_id", readonly=True)
    production_profit = fields.Monetary("Production Profit", currency_field="currency_usd_id", readonly=True)
    margin = fields.Float("Margin", readonly=True)

    def _compute_currency_usd_id(self):
        for record in self:
            record.currency_usd_id = self.env.ref('base.USD')

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        result = super(MoronSaleReport, self).read_group(domain, fields, groupby, offset, limit, orderby, lazy)
        for line in result:
            if line['revenue'] > 0.0:
                line['margin'] = (line['production_profit'] / line['revenue']) * 100
            else:
                if line['production_profit'] > 0.0:
                    line['margin'] = 100.0
                else:
                    line['margin'] = 0.0
        return result

    def _query(self):
        return """
        WITH data_existing AS (
            SELECT
                ROW_NUMBER() OVER() as id,
                pp.id as project_id,
                pp.partner_id,
                am_client.invoice_date,
                so.id as moron_sale_order_id,
                am_client.id as client_invoice_id,
                am_client.amount_total_signed as revenue,
                NULL as moron_purchase_order_id,
                NULL as contributor_invoice_id,
                0 as project_cost,
                am_client.amount_total_signed as production_profit,
                0 as margin
            FROM project_project pp
                JOIN moron_sale_order so ON so.project_id = pp.id
                JOIN account_move am_client ON am_client.id = so.client_invoice_id
            WHERE so.status IN ('invoiced', 'completed')

            UNION ALL

            SELECT
                ROW_NUMBER() OVER() + (SELECT COUNT(*) FROM moron_sale_order WHERE status IN ('invoiced', 'completed')) as id,
                pp.id as project_id,
                pp.partner_id,
                am_contributor.invoice_date,
                NULL as moron_sale_order_id,
                NULL as client_invoice_id,
                0 as revenue,
                po.id as moron_purchase_order_id,
                am_contributor.id as contributor_invoice_id,
                - am_contributor.amount_total_signed as project_cost,
                am_contributor.amount_total_signed as production_profit,
                0 as margin
            FROM project_project pp
                JOIN project_task po ON po.project_id = pp.id
                JOIN account_move am_contributor ON am_contributor.id = po.contributor_invoice_id
            WHERE po.payment_status IN ('invoiced', 'paid')
        )

        SELECT * FROM data_existing

        UNION ALL
        
        -- Tạo dòng dữ liệu cho những tháng không có hóa đơn (trong 12 tháng gần nhất)
        SELECT
            (SELECT COALESCE(MAX(id), 0) FROM data_existing) + ROW_NUMBER() OVER() as id,
            NULL as project_id,
            NULL as partner_id,
            date_trunc('month', months)::date as invoice_date,
            NULL as moron_sale_order_id,
            NULL as client_invoice_id,
            0 as revenue,
            NULL as moron_purchase_order_id,
            NULL as contributor_invoice_id,
            0 as project_cost,
            0 as production_profit,
            0 as margin
        FROM (
            -- Tạo chuỗi 12 tháng gần nhất
            SELECT generate_series(
                date_trunc('month', CURRENT_DATE - interval '11 months'),
                date_trunc('month', CURRENT_DATE),
                interval '1 month'
            ) as months
        ) m
        WHERE NOT EXISTS (
            -- Kiểm tra xem tháng này đã có trong data_existing chưa
            SELECT 1 
            FROM data_existing 
            WHERE date_trunc('month', data_existing.invoice_date) = date_trunc('month', m.months)
        )
        """

    def init(self):
        """
        """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW %s AS (%s)
        """ % (self._table, self._query()))
