import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class ResPartner(models.Model):
    _inherit = ["res.partner"]

    moron_project_ids = fields.One2many("project.project", "partner_id", string="Projects")

    moron_invoice_ids = fields.Many2many("account.move", string="Invoices",
                                        compute="_compute_moron_invoice_ids")

    customerId = fields.Char(string="Customer ID")
    moron_salesperson_ids = fields.Many2many("res.users", string="Salesperson")
    payment_term_id = fields.Many2one("account.payment.term", string="Payment Term")

    # Payment Method
    paypal = fields.Char('PayPal ID')
    transferwise_id = fields.Char('Wise ID')
    bank_account_number = fields.Char('Bank Account Number')
    bank_name = fields.Char('Bank Name')
    iban = fields.Char('IBAN')
    swift = fields.Char('SWIFT')
    bank_address = fields.Char('Bank Address')
    payment_method = fields.Selection(selection=[('paypal', 'Paypal'),
                                                 ('transferwise', 'Wise'),
                                                 ('bank', 'Bank Transfer')])

    @api.depends("moron_project_ids")
    def _compute_moron_invoice_ids(self):
        for r in self:
            r.moron_invoice_ids = r.moron_project_ids.client_invoice_id
