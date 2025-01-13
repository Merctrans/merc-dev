# -*- coding: utf-8 -*-

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
    _rec_name = "name"
    _description = "Services offered by MercTrans"

    department_list = [
        ("localization", "Localization"),
        ("marketing", "Marketing"),
        ("development", "Development"),
    ]
    department = fields.Selection(string="Department", selection=department_list)
    name = fields.Char("Services")


class MerctransProject(models.Model):
    """
    A model representing projects managed by MercTrans.

    This class extends the functionality of the 'project.project' model
    to cater specifically to the needs of MercTrans projects. It includes
    features such as different work units, payment statuses, and calculation
    of project values and margins. It also handles the creation of unique
    project IDs and the computation of various financial metrics.

    Attributes:
        _inherit (list): Inherited model name in the Odoo framework.
        work_unit_list (list of tuples): A predefined list of work units for projects.
        payment_status_list (list of tuples): A predefined list of payment statuses.
        job_id (fields.Char): Field for the unique project identifier.
        service (fields.Many2many): Relationship to the 'merctrans.services' model.
        source_language (fields.Many2one): Field for the source language of the project.
        target_language (fields.Many2many): Field for the target languages of the project.
        discount (fields.Integer): Field for any discount applied to the project.
        work_unit (fields.Selection): Field for selecting a work unit from the work_unit_list.
        volume (fields.Integer): Field for the volume of the project.
        currency_id (fields.Many2one): Field for the currency used in the project.
        sale_rate (fields.Float): Field for the sale rate of the project.
        job_value (fields.Monetary): Computed field for the total value of the project.
        payment_status (fields.Selection): Field for the payment status of the project.
        po_value (fields.Monetary): Computed field for the Purchase Order value of the project.
        margin (fields.Float): Computed field for the margin of the project.

    Methods:
        create(vals): Creates a new project with a unique ID.
        _compute_job_value(): Computes the job value based on volume, sale rate, and discount.
        _compute_po_value(): Computes the PO value from all associated tasks.
        _compute_margin(): Calculates the project margin.
        _compute_receivable(): Calculates the receivable of the project.
    """

    _inherit = ["project.project"]

    work_unit_list = [
        ("word", "Word"),
        ("hour", "Hour"),
        ("page", "Page"),
        ("job", "Job"),
    ]

    # project_status_list = [('potential', 'Potential'),
    #                        ('confirmed', 'Confirmed'),
    #                        ('in progress', 'In Progress'), ('in qa', 'In QA'),
    #                        ('delivered', 'Delivered'),
    #                        ('canceled', 'Canceled')]

    payment_status_list = [
        ("unpaid", "Unpaid"),
        ("invoiced", "Invoiced"),
        ("paid", "Paid"),
    ]

    job_id = fields.Char(
        "Project Id",
        default=lambda self: "New",
        readonly=True,
        index=True,
        required=True,
        copy=False,
        tracking=True,
    )

    # services contain tags

    service = fields.Many2many("merctrans.services", string="Services", tracking=True)
    source_language = fields.Many2one(
        "res.lang", string="Source Language", tracking=True
    )
    target_language = fields.Many2many(
        "res.lang", string="Target Language", tracking=True
    )
    discount = fields.Integer("Discount (%)", tracking=True)

    # add discount field
    # fixed job

    work_unit = fields.Selection(
        string="Work Unit", selection=work_unit_list, tracking=True
    )
    volume = fields.Float("Project Volume", tracking=True)
    currency_id = fields.Many2one("res.currency", string="Currency*", required=True, tracking=True, store=True, readonly=False)
    sale_rate = fields.Monetary("Sale Rate", tracking=True, currency_field="currency_id")
    job_value = fields.Monetary(
        "Project Value",
        compute="_compute_job_value",
        currency_field="currency_id",
        store=True,
        readonly=True,
        tracking=True,
    )
    # project_status = fields.Selection(string='Project Status',
    #                                   selection=project_status_list)
    payment_status = fields.Selection(
        string="Payment Status", selection=payment_status_list, tracking=True
    )
    po_value = fields.Monetary(
        "PO Value",
        compute="_compute_po_value",
        currency_field="currency_id",
        store=True,
        readonly=True,
        tracking=True
    )
    margin = fields.Float(
        "Project Margin",
        compute="_compute_margin",
        store=True,
        readonly=True,
        tracking=True,
        digits=(16, 3)
    )

    @api.model
    def create(self, vals):
        """Creates a new project.

        This method creates a new project and assigns it a unique project ID.
        It is automatically triggered when a new project is created.

        Parameters:
            vals: A dictionary containing the values of the fields on the project.

        Returns:
            project: The newly created project.
        """
        if self.env.user.has_group("morons.group_contributors"):
            raise AccessError("You do not have permission to create projects.")

        if vals.get("job_id", "New") == "New":
            vals["job_id"] = self.env["ir.sequence"].next_by_code(
                "increment_project_id"
            )

        return super(MerctransProject, self).create(vals)

    def unlink(self):
        if self.env.user.has_group("morons.group_contributors"):
            raise AccessError("You do not have permission to delete projects.")
        
        res = super(MerctransProject, self).unlink()
            
        return res 
    
    def button_delete(self):
        
        if self.env.user.has_group("morons.group_contributors"):
            raise AccessError("You do not have permission to delete projects.")
        res = super(MerctransProject, self).unlink()
        if res:
            return {
            'type': 'ir.actions.act_url',
            'url': 'https://moron.merctrans.vn/web#action=337&model=project.project&view_type=list&cids=1&menu_id=195',
            'target': 'self',  
            }
        
    def write(self, vals):
        if self.env.user.has_group("morons.group_contributors") and any(
            field_name in vals
            for field_name in [
                "source_language",
                "payment_status",
                "sale_rate",
                "currency",
                "volume",
                "work_unit",
                "discount",
                "target_language",
                "service",
                'tag_ids',
                'partner_id',
                'date_start',
                'user_id'
            ]
        ):
            raise AccessError("You do not have permission to edit projects.")
        old_services = self.mapped("service")
        old_target_language = self.mapped("target_language")
        old_tag_ids = self.mapped("tag_ids")

        res = super(MerctransProject, self).write(vals)

        new_services = self.mapped("service")
        new_target_language = self.mapped("target_language")
        new_tag_ids = self.mapped("tag_ids")
        # Activities logs
        if new_services != old_services:
            for project in self:
                added_services = new_services - old_services
                removed_services = old_services - new_services

                for added_service in added_services:
                    project.message_post(body="Added service: %s" % added_service.name)

                for removed_service in removed_services:
                    project.message_post(
                        body="Removed service: %s" % removed_service.name
                    )

        if new_target_language != old_target_language:
            for project in self:
                added_languages = new_target_language - old_target_language
                removed_languages = old_target_language - new_target_language

                for added_language in added_languages:
                    project.message_post(
                        body="Added target language: %s" % added_language.name
                    )

                for removed_language in removed_languages:
                    project.message_post(
                        body="Removed target language: %s" % removed_language.name
                    )

        if new_tag_ids != old_tag_ids:
            for project in self:
                added_ids = new_tag_ids - old_tag_ids
                removed_ids = old_tag_ids - new_tag_ids

                for added_id in added_ids:
                    project.message_post(body="Added tag: %s" % added_id.name)

                for removed_id in removed_ids:
                    project.message_post(body="Removed tag: %s" % removed_id.name)

        return res

    @api.depends("volume", "sale_rate", "discount")
    def _compute_job_value(self):
        """Computes the job value of the project.

        Parameters:
            volume: The volume of the project.
            sale_rate: The sale rate of the project.
            discount: The discount of the project (if any).

        Returns:
            None: Updates the 'job_value' field of each project record with the calculated job value.
        """
        for project in self:
            project.job_value = (
                (100 - project.discount) / 100 * project.volume * project.sale_rate
            )

    @api.depends("tasks", 'tasks.po_value_by_project_currency', 'currency_id')
    def _compute_po_value(self):
        """Computes the total Purchase Order (PO) value of the project.

        Parameters:
            tasks: The tasks associated with the project.

        Returns:
            None: Updates the 'po_value' field of each project record with the calculated sum.
        """
        for project in self:
            project.po_value = sum(project.tasks.mapped("po_value_by_project_currency"))

    @api.depends("po_value", "job_value")
    def _compute_margin(self):
        """Computes the margin of the project.

        Parameters:
            po_value: The total PO value of the project.
            job_value: The total job value of the project.

        Returns:
            None: Updates the 'margin' field of each project record with the calculated margin.
        """
        for project in self:
            if project.job_value and project.po_value:
                project.margin = (
                    project.job_value - project.po_value
                ) / project.job_value
            else:
                project.margin = 0

    @api.depends("po_value", "job_value")
    def _compute_receivable(self):
        """Computes the receivable of the project.

        Parameters:
            po_value: The total PO value of the project.
            job_value: The total job value of the project.

        Returns:
            None: Updates the 'receivable' field of each project record with the calculated receivable.
        """
        for project in self:
            if project.po_value and project.job_value:
                project.receivable = project.job_value - project.po_value
            else:
                project.receivable = 0


    @api.model
    def search(self, args, **kwargs):
        if self.env.user.has_group("base.group_system") or self.env.user.has_group("morons.group_pm") :
            pass
        else:
            args += [("user_id", "=", self.env.user.id)] 
        return super(MerctransProject, self).search(args, **kwargs)
    def _get_dynamic_domain(self):
        accountant_group = self.env.ref("morons.group_accountants")
        accountant_user_ids = accountant_group.users.ids
        return [("create_uid", "not in", accountant_user_ids)]
    # Alert negative
    @api.constrains("volume", "sale_rate", "discount")
    def _check_positive_values(self):
        for task in self:
            if task.volume < 0:
                raise ValidationError("Project volume cannot be negative.")
            if task.sale_rate < 0:
                raise ValidationError("Project sale rate cannot be negative.")
            if task.discount < 0:
                raise ValidationError("Project discount cannot be negative.")
    
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
    user_ids = fields.Many2many(
        "res.users",
        relation="custom_project_task_user_rel",
        column1="task_id",
        column2="user_id",
        string="Assignees*",
        context={"active_test": False},
        tracking=True,
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
        string="Stage*", selection=po_status_list, required=True,tracking= True
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
    name = fields.Char(compute="_compute_name", readonly=False,tracking= True)

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
            if len(task.project_id) == 1:
                task.name = task.project_id.display_name
            else:
                task.name = ", ".join(
                    project.display_name for project in task.project_id
                )

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
