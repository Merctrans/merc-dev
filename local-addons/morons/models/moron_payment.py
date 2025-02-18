from odoo import models, fields, api


class MercTransPayment(models.Model):
    _inherit = "account.payment"
    
    moron_client_invoice_id = fields.Many2one("account.move", string="Customer Invoice")
    moron_contributor_invoice_id = fields.Many2one("account.move", string="Contributor Invoice")
