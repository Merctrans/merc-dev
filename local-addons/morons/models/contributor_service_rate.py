from odoo import models, fields, api
from odoo.tools import format_amount


class ContributorServiceRate(models.Model):
    _name = 'contributor.service.rate'
    _description = 'Contributor Service Rate'
    _order = 'sequence'

    contributor_id = fields.Many2one('res.users', string='Contributor')
    service_id = fields.Many2one('merctrans.services', string='Service')
    rate = fields.Monetary('Rate')
    note = fields.Text('Note')
    currency_id = fields.Many2one(related='contributor_id.currency', store=True)
    work_unit_list = [
        ("word", "Word"),
        ("hour", "Hour"),
        ("page", "Page"),
        ("job", "Job"),
    ]
    work_unit = fields.Selection(string="Work Unit", selection=work_unit_list, required=True)
    sequence = fields.Integer(default=10)

    @api.depends('work_unit', 'rate')
    def _compute_display_name(self):
        for r in self:
            rate_str = format_amount(self.env, r.rate, r.currency_id)
            r.display_name = "%s (%s / %s)" % (r.service_id.name, rate_str, r.work_unit)
