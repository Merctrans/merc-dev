from odoo import models, fields


class ContributorServiceRate(models.Model):
    _name = 'contributor.service.rate'
    _description = 'Contributor Service Rate'

    contributor_id = fields.Many2one('res.users', string='Contributor')
    service_id = fields.Many2one('merctrans.services', string='Service')
    rate = fields.Monetary('Rate')
    note = fields.Text('Note')
    currency_id = fields.Many2one(related='contributor_id.currency', store=True)
