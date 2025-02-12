# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import Command, models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import frozendict


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    moron_client_invoice_id = fields.Many2one("account.move", string="Invoice", readonly=True)
    moron_contributor_invoice_id = fields.Many2one("account.move", string="Invoice", readonly=True)

    def _create_payments(self):
        payments = super()._create_payments()
        if self.moron_client_invoice_id:
            payments.write({"moron_client_invoice_id": self.moron_client_invoice_id.id})
        if self.moron_contributor_invoice_id:
            payments.write({"moron_contributor_invoice_id": self.moron_contributor_invoice_id.id})
        return payments
