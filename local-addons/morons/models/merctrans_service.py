from odoo import models, fields


class MercTransServices(models.Model):
    """
    A model representing the different services offered by MercTrans.

    This class encapsulates the various services that MercTrans provides,
    categorized into different departments. It serves as a way to manage
    and access the services information in an organized manner.

    Attributes:
        _name (str): Internal name of the model in the Odoo framework.
        _rec_name (str): Field to use for record name.
        _description (str): A brief description of the model's purpose.
        department_list (list of tuples): A predefined list of departments.
        department (fields.Selection): Field for selecting a department from the department_list.
        name (fields.Char): Field for the name of the service.
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
