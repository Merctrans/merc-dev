from odoo import models, fields, api

class ExchangeRate(models.TransientModel):
    _name = 'morons.exchange_rate'
    _description = 'A model representing exchange rates in the MercTrans system.'

    base_currency = fields.Many2one('res.currency', string='Base Currency', required=True)
    target_currency = fields.Many2one('res.currency', string='Target Currency', required=True)
    exchange_rate = fields.Float(string='Exchange Rate', required=True)

