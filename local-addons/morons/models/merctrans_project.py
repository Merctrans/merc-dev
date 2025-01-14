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

    # Override default value as the setting tab will be hidden on view
    privacy_visibility = fields.Selection(default="followers")
    description = fields.Text(default="WARNING: This field will be visible to Contributors when they are assigned to POs. Please check for sensitive information before submitting.")

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
