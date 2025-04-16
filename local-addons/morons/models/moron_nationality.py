from odoo import models, fields


class MoronNationality(models.Model):
    _name = 'moron.nationality'
    _description = 'Nationality Management'

    name = fields.Char(string='Name', required=True)
