from odoo import models, fields, api
from odoo.exceptions import AccessError, RedirectWarning
import logging
from odoo.exceptions import ValidationError
logger = logging.getLogger(__name__)

""""TODO
- Inherit to project.project
- User Project to generate metadata
- Task to delegate tasks to Contributors

"""

class MerctransTask(models.Model):
    """
    A model representing tasks within Merctrans projects.

    This class extends the 'project.task' model of Odoo, tailored for the specific needs of
    Merctrans projects. It includes functionality for managing purchase order statuses, work units,
    payment statuses, and various other task-related details. Key features include the ability to
    compute the value of tasks based on volume and rate, and handling the source and target languages
    for tasks in translation projects.

    Attributes:
        _inherit (str): Inherited model name in the Odoo framework.
        po_status_list (list of tuples): A predefined list of possible statuses for purchase orders.
        work_unit_list (list of tuples): A predefined list of work units applicable to tasks.
        payment_status_list (list of tuples): A predefined list of payment statuses for tasks.
        rate (fields.Float): Field for the rate applicable to the task.
        service (fields.Many2many): Relationship to the 'merctrans.services' model, indicating services involved in the task.
        source_language (fields.Many2one): Computed field for the source language of the task, derived from the associated project.
        target_language (fields.Many2many): Field for the target languages of the task.
        work_unit (fields.Selection): Field for selecting a work unit from the work_unit_list.
        volume (fields.Integer): Field for the volume of work associated with the task.
        po_value (fields.Float): Computed field for the Purchase Order value of the task.
        payment_status (fields.Selection): Field for the payment status of the task.
        currency (fields.Char): Computed field for the currency used in the task.

    Methods:
        _invert_get_source_lang(): Placeholder method for inverse computation of source language. (TODO)
        _invert_get_target_lang(): Placeholder method for inverse computation of target language.  (TODO)
        _compute_po_value(): Computes the Purchase Order value of the task based on volume and rate.
        _get_source_lang(): Computes the source language of the task based on its associated project.
        _compute_currency_id(): Computes the currency used in the task based on the users assigned to it.
    """

    _inherit = "project.task"

    # Override to set attrs
    user_ids = fields.Many2many(
        string="Assignees*",
        domain="[('share', '=', False), ('active', '=', True)]",
        required=True,
    )

    po_status_list = [
        ("in progress", "In Progress"),
        ("completed", "Completed"),
        ("canceled", "Canceled"),
    ]

    work_unit_list = [
        ("word", "Word"),
        ("hour", "Hour"),
        ("page", "Page"),
        ("job", "Job"),
    ]

    payment_status_list = [
        ("unpaid", "Unpaid"),
        ("invoiced", "Invoiced"),
        ("paid", "Paid"),
    ]
    stages_id = fields.Selection(
        string="Completion Status*", selection=po_status_list, required=True,tracking= True
    )

    rate = fields.Monetary(string="Rate*", tracking=True, currency_field="currency_id")
    service = fields.Many2many("merctrans.services",tracking= True)
    source_language = fields.Many2one(
        "res.lang",
        string="Source Language",
        compute="_get_source_lang",
        inverse="_invert_get_source_lang",
        tracking= True,
        
    )
    target_language = fields.Many2many(
        "res.lang",
        string="Target Language",
        tracking= True
    )
    
    work_unit = fields.Selection(
        string="Work Unit*", selection=work_unit_list, required=True,tracking= True
    )
    volume = fields.Float(string="Volume*", required=True, default=0, tracking= True)
    po_value = fields.Monetary("PO Value", default=0,
        compute="_compute_po_value", store=True, readonly=True,
        tracking=True, currency_field="currency_id"
    )
    po_value_by_project_currency = fields.Monetary("PO Value (By Project)",
        compute="_compute_po_value_by_project_currency", store=True, readonly=True,
        currency_field="project_currency_id"
    )
    po_value_by_project_currency_string = fields.Char("PO Value (By Project)",
        compute="_compute_po_value_by_project_currency_string",
    )
    show_po_value_currency_string = fields.Boolean("Show PO Value Currency String", default=False, compute="_compute_show_po_value_currency_string")

    payment_status = fields.Selection(
        string="Payment Status*",
        selection=payment_status_list,
        required=True,
        default="unpaid",
        tracking= True
    )
    currency_id = fields.Many2one("res.currency", string="Currency", compute="_compute_currency_id", store=True, tracking= True, readonly=False)
    project_currency_id = fields.Many2one("res.currency", related="project_id.currency_id", store=True, readonly=True)
    name = fields.Char(compute="_compute_name", tracking= True, store=True)

    def _invert_get_source_lang(self):
        pass

    def _invert_get_target_lang(self):
        pass

    @api.depends("volume", "rate")
    def _compute_po_value(self):
        for task in self:
            task.po_value = task.volume * task.rate

    @api.depends("project_id.currency_id", "currency_id", 'po_value')
    def _compute_po_value_by_project_currency(self):
        """
        If the currency of the PO is different from the currency of the Project, conversion is necessary as follows:
            1. Convert the currency of the PO to the company's currency
            2. Convert the company's currency to the currency on the Project
        """
        for record in self:
            company_currency = record.project_id.company_id.currency_id
            project_currency = record.project_id.currency_id
            po_currency = record.currency_id

            project_po_value = record.po_value

            if po_currency != project_currency:
                # 1. Convert the PO currency to the company's currency
                if po_currency != company_currency:
                    project_po_value = po_currency._convert(
                        project_po_value,
                        company_currency,
                        record.project_id.company_id,
                        fields.Date.context_today(record)
                    )
            
                # 2. Convert the company's currency to the currency on the Project
                if company_currency != project_currency:
                    project_po_value = company_currency._convert(
                        project_po_value,
                        project_currency,
                        record.project_id.company_id,
                        fields.Date.context_today(record)
                    )
            record.po_value_by_project_currency = project_po_value

    @api.depends("po_value_by_project_currency")
    def _compute_po_value_by_project_currency_string(self):
        for record in self:
            po_value_str = record.project_id.currency_id.format(record.po_value_by_project_currency)
            record.po_value_by_project_currency_string = "( = %s )" % po_value_str

    @api.depends("currency_id", "project_currency_id")
    def _compute_show_po_value_currency_string(self):
        for record in self:
            record.show_po_value_currency_string = record.currency_id != record.project_currency_id

    @api.depends("project_id")
    def _get_source_lang(self):
        for task in self:
            if self.project_id:
                self.source_language = self.project_id.source_language

    @api.depends("project_id")
    def _compute_name(self):
        for task in self:
            task.name = task.project_id.display_name

    @api.depends("user_ids")
    def _compute_currency_id(self):
        for record in self:
            if record.user_ids.currency:
                record.currency_id = record.user_ids.currency[0]
            else:
                record.currency_id = record.project_id.currency_id

    @api.model
    def write(self, vals):
        if self.env.user.has_group("morons.group_contributors"):
            for task in self:
                for user in task.user_ids:
                    if not user.has_group("morons.group_contributors"):
                        raise AccessError(
                            "Only users belonging to the 'contributors' group can edit this task."
                        )
        return super(MerctransTask, self).write(vals)
    def unlink(self):
        if self.env.user.has_group("morons.group_contributors"):
            for task in self:
                if task.create_uid.has_group("morons.group_contributors"):
                    if task.create_uid != self.env.user:
                        raise AccessError("You do not have permission to delete this task.")
        return super(MerctransTask, self).unlink()
    
    def action_test(self):
        return{
            "type": "ir.actions.act_window",
            "res_model": "project.project",
            "views": [[False, "tree"]],
            "res_id": 'project.open_view_project_all',
            "target": "new",
            }
    #Alert negative   
    @api.constrains("volume","rate")
    def _check_positive_values(self):
        for task in self:
            if task.volume < 0:
                raise ValidationError("Project Volume cannot be negative.")
            if task.rate < 0:
                raise ValidationError("Project Rate cannot be negative.")

    @api.onchange("project_id")
    def onchange_project_id(self):
        self.service = self.project_id.service
        self.source_language = self.project_id.source_language
        self.target_language = self.project_id.target_language
        self.work_unit = self.project_id.work_unit
