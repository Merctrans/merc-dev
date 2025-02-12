from odoo import models, fields, api


class MoronSaleOrderLine(models.Model):
    _name = "moron.sale.order.line"
    _description = "Moron Sale Order Line"

    sale_order_id = fields.Many2one('moron.sale.order', string='Sale Order')
    company_id = fields.Many2one(related='sale_order_id.company_id', store=True)
    currency_id = fields.Many2one(related='sale_order_id.currency_id', store=True)
    name = fields.Char(string='Project Name')
    volume = fields.Float(string='Volume')
    work_unit = fields.Selection(string="Work Unit",
        selection=[("word", "Word"), ("hour", "Hour"), ("page", "Page"), ("job", "Job")],
        tracking=True
    )
    sale_rate = fields.Monetary(string='Sale Rate')
    project_value = fields.Monetary(string='Total', compute='_compute_project_value', store=True)

    @api.depends('volume', 'sale_rate')
    def _compute_project_value(self):
        for line in self:
            line.project_value = line.volume * line.sale_rate
