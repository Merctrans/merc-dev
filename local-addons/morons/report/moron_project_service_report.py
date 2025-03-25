from odoo import models, fields, api
from odoo import tools


class MoronProjectLangReport(models.Model):
    _name = "moron.project.lang.report"
    _description = "Moron Project Language Report"
    _auto = False

    name_display = fields.Char("Services", readonly=True)
    project_id = fields.Many2one("project.project", string="Project", readonly=True)
    client_invoice_id = fields.Many2one('account.move', string='Client Invoice', readonly=True)
    revenue = fields.Monetary("Revenue", readonly=True, currency_field='currency_usd_id')
    source_language = fields.Many2one("res.lang", string="Source Language", readonly=True)
    target_language = fields.Many2one("res.lang", string="Target Language", readonly=True)
    currency_usd_id = fields.Many2one('res.currency', "USD", readonly=True,
                                        compute="_compute_currency_usd_id")

    @api.depends('client_invoice_id')
    def _compute_currency_usd_id(self):
        for record in self:
            if record.client_invoice_id:
                record.currency_usd_id = record.company_id.currency_id or self.env.ref('base.USD')
            else:
                record.currency_usd_id = self.env.ref('base.USD')

    def _query(self):
        return """
        SELECT 
            ROW_NUMBER() OVER() as id,
            pp.id as project_id,
            pp.source_language as source_language,
            tl.res_lang_id as target_language,
            CONCAT(
                (SELECT name FROM res_lang WHERE id = pp.source_language),
                ' -> ',
                (SELECT name FROM res_lang WHERE id = tl.res_lang_id)
            ) as name_display,
            am_client.amount_total_signed as revenue
        FROM 
            project_project pp
            -- Join với bảng quan hệ many2many của target language
            LEFT JOIN project_project_res_lang_rel tl ON pp.id = tl.project_project_id
            LEFT JOIN moron_sale_order so ON so.project_id = pp.id
            LEFT JOIN account_move am_client ON am_client.id = so.client_invoice_id
        WHERE 
            pp.active = true
        """

    def init(self):
        """
        """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW %s AS (%s)
        """ % (self._table, self._query()))
