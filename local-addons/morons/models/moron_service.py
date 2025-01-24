from odoo import models, fields


class MercTransServices(models.Model):
    """
    A model representing the different services offered by MercTrans.

    This class encapsulates the various services that MercTrans provides,
    categorized into different departments. It serves as a way to manage
    and access the services information in an organized manner.
    """

    _name = "merctrans.services"
    _description = "Services offered by MercTrans"

    name = fields.Char("Services")
    department_list = [
        ("localization", "Localization"),
        ("marketing", "Marketing"),
        ("development", "Development"),
    ]
    department = fields.Selection(string="Department", selection=department_list)
