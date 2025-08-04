from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import format_date
import logging
_logger = logging.getLogger(__name__)


class MerctransTask(models.Model):
    _inherit = "project.task"
    _description = "Purchase Order"

    contributor_id = fields.Many2one("res.users", string='Contributor',
                                        domain="[('share', '=', False), ('active', '=', True), ('contributor', '=', True)]")
    contributor_send_email_ids = fields.Many2many("res.users", string='Send to contributors',
                                                 domain="[('share', '=', False), ('active', '=', True), ('contributor', '=', True)]",
                                                 help="Send job confirmation email to all selected contributors.")

    po_status_list = [
        ("new", "New"),
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
        string="Completion Status", selection=po_status_list, required=True,tracking= True, default="new"
    )

    rate = fields.Monetary(string="Rate*", tracking=True, currency_field="currency_id")
    service = fields.Many2many("merctrans.services",tracking= True)
    source_language = fields.Many2one("res.lang", string="Source Language", tracking= True, readonly=True)
    target_language = fields.Many2one("res.lang", string="Target Language", tracking= True, compute_sudo=True,
                                        domain="[('id', 'in', target_language_selected)]")
    target_language_selected = fields.Many2many("res.lang", string="Target Language Selected",
                                                compute="_compute_target_language_selected", compute_sudo=True)
    
    work_unit = fields.Selection(
        string="Work Unit*", selection=work_unit_list, required=True,tracking= True
    )
    volume = fields.Float(string="Volume*", required=True, default=0, tracking= True)
    po_value = fields.Monetary("PO Value", default=0,
        compute="_compute_po_value", store=True, readonly=True,
        tracking=True, currency_field="currency_id"
    )
    po_value_by_project_currency = fields.Monetary("PO Value (By Project)",
        compute="_compute_po_value_by_project_currency", store=True, readonly=True, compute_sudo=True,
        currency_field="project_currency_id"
    )
    po_value_by_project_currency_string = fields.Char("PO Value (By Project)",
        compute="_compute_po_value_by_project_currency_string", compute_sudo=True,
    )
    show_po_value_currency_string = fields.Boolean("Show PO Value Currency String", default=False, compute="_compute_show_po_value_currency_string", compute_sudo=True)

    payment_status = fields.Selection(
        string="Payment Status*",
        selection=payment_status_list,
        required=True,
        default="unpaid",
        tracking= True,
        compute="_compute_payment_status", store=True, compute_sudo=True
    )
    currency_id = fields.Many2one("res.currency", string="Currency", tracking= True)
    project_currency_id = fields.Many2one("res.currency", related="project_id.currency_id", store=True, readonly=True, compute_sudo=True)
    name = fields.Char(string="Name", required=True, tracking= True, default="New")

    contributor_invoice_id = fields.Many2one("account.move", string="Contributor Invoice")

    show_warning_deadline = fields.Text(string="Show Warning Deadline", default="", compute="_compute_show_warning_deadline", compute_sudo=True)

    @api.constrains("volume","rate")
    def _check_positive_values(self):
        for task in self:
            if task.volume < 0:
                raise ValidationError(_("Project Volume cannot be negative."))
            if task.rate < 0:
                raise ValidationError(_("Project Rate cannot be negative."))

    @api.depends("date_deadline")
    def _compute_show_warning_deadline(self):
        for r in self:
            msg = ''
            if r.date_deadline and r.project_id.date_start and r.date_deadline < r.project_id.date_start:
                date_start = format_date(self.env, r.project_id.date_start)
                date_end = format_date(self.env, r.project_id.date)
                msg = _("Deadline must be within Project timeline: %s - %s") % (date_start, date_end)
            elif r.date_deadline and r.project_id.date and r.date_deadline > r.project_id.date:
                date_start = format_date(self.env, r.project_id.date_start)
                date_end = format_date(self.env, r.project_id.date)
                msg = _("Deadline must be within Project timeline: %s - %s") % (date_start, date_end)
            r.show_warning_deadline = msg

    @api.depends("volume", "rate")
    def _compute_po_value(self):
        """
        Lưu ý: khi thay đổi công thức ở đây, cần phải điều chỉnh lại logic tạo hóa đơn để đảm bảo số tiền của PO Value = số tiền của hóa đơn
        """
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
    def _compute_target_language_selected(self):
        for r in self:
            r.target_language_selected = r.project_id.target_language

    @api.onchange("contributor_id", "project_id")
    def _onchange_contributor_id(self):
        if self.contributor_id.currency:
            self.currency_id = self.contributor_id.currency[0]
        else:
            self.currency_id = self.project_id.currency_id

    @api.depends("contributor_invoice_id", 'contributor_invoice_id.payment_state')
    def _compute_payment_status(self):
        for r in self:
            payment_status = "unpaid"
            if r.contributor_invoice_id:
                payment_status = "invoiced"
                if r.contributor_invoice_id.payment_state == "paid":
                    payment_status = "paid"
            r.payment_status = payment_status

    @api.onchange("project_id")
    def onchange_project_id(self):
        self.service = self.project_id.service
        self.source_language = self.project_id.source_language
        self.target_language = self.project_id.target_language[:1]
        self.work_unit = self.project_id.work_unit
        self.volume = self.project_id.volume
        self.rate = self.project_id.sale_rate
        self.date_deadline = self.project_id.date

    def action_complete(self):
        self.write({"stages_id": "completed"})

    def action_send_email_to_contributors(self):
        for r in self.filtered(lambda c: not c.contributor_id and c.stages_id == 'new'):
            for contributor in r.contributor_send_email_ids:
                r._send_email_to_contributor(contributor)

    def _send_email_to_contributor(self, contributor):
        if not contributor:
            return
        # Utility method to send assignation notification upon writing/creation.
        email_template = self.env.ref('morons.email_template_po_assignment', raise_if_not_found=False)
        if not email_template:
            return
        task_model_description = self.env['ir.model']._get(self._name).display_name

        email_values = {
            'email_cc': False,
            'auto_delete': True,
            'message_type': 'user_notification',
            'recipient_ids': [],
            'partner_ids': [],
            'scheduled_date': False,
            'email_to': contributor.email
        }

        with self.env.cr.savepoint():
            force_send = not(self.env.context.get('import_file', False))
            email_template.send_mail(self.id, force_send=force_send, raise_exception=False, email_values=email_values)
        _logger.info("Emailed PO <%s> information to contributor <%s>", self.name, contributor.email)

    def action_in_progress(self):
        for r in self:
            if not r.contributor_id:
                raise UserError(_("Please select a contributor before proceeding to 'In Progress': %s") % r.name)
        self.write({"stages_id": "in progress"})

    def action_set_to_new(self):
        self = self.filtered(lambda r: r.stages_id == "canceled")
        self.write({"stages_id": "new"})

    def action_cancel(self):
        is_contributor = self.env.user.has_group("morons.group_contributors") and not self.env.user.has_group("morons.group_pm")
        for r in self:
            if r.contributor_invoice_id:
                raise ValidationError("Purchase order '%s' already has a contributor invoice. Please delete the contributor invoice first." % r.name)
        
            if is_contributor:
                if self.env.user == r.contributor_id:
                    r.sudo().write({"stages_id": "canceled"})
                else:
                    raise ValidationError(_("You cannot cancel a contributor invoice for another contributor: %s") % r.contributor_id.name)
            else:
                r.write({"stages_id": "canceled"})

    def action_create_invoice(self):
        """
        Cho phép tạo invoice cho 1 hoặc nhiều PO:
        - Nếu PO đã có invoice => cảnh báo
        - Nếu PO không có invoice => tạo invoice:
            - Tạo invoice gộp cho nhiều PO nếu có nhiều PO
        """
        # check common
        for r in self:
            if r.stages_id != "completed":
                raise ValidationError("Purchase order '%s' must be completed before creating an invoice." % r.name)
            if not r.contributor_id:
                raise ValidationError("A contributor must be designated for purchase order '%s'." % r.name)
            if r.contributor_invoice_id:
                raise ValidationError(_("This purchase order '%s' already has an invoice.") % r.name)


        invoices = self.env["account.move"]
        for contributor in self.contributor_id:
            AccountMove = self.env["account.move"]
            # check contributor
            purchase_orders = self.filtered(lambda po: po.contributor_id == contributor)
            if len(purchase_orders.currency_id) > 1:
                raise ValidationError(_("You cannot create an invoice for multiple currencies: %s") % purchase_orders.mapped("name"))
            if self.env.user.has_group("morons.group_contributors"):
                if self.env.user == contributor:
                    AccountMove = AccountMove.sudo()
                else:
                    raise ValidationError(_("You cannot create an contributor invoice for another contributor: %s") % contributor.name)

            invoice_line_data = []
            for po in purchase_orders:
                invoice_line_data.append((0, 0, {
                    'name': "%s - %s - %s: %s" % (
                        po.sudo().project_id.name, 
                        po.name,
                        dict(po._fields['work_unit'].selection).get(po.work_unit),
                        ", ".join(po.service.mapped("name"))
                    ),
                    'quantity': po.volume,
                    'price_unit': po.rate,
                    'tax_ids': False
                }))
            
            invoice = AccountMove.create({
                'partner_id': contributor.partner_id.id,
                'move_type': 'in_invoice',
                'currency_id': purchase_orders.currency_id.id,
                'date': fields.Date.context_today(self),
                'invoice_line_ids': invoice_line_data
            })
            if invoice:
                purchase_orders.sudo().write({"contributor_invoice_id": invoice.id})
                invoices |= invoice


        if len(invoices) == 1:
            if self.env.user.has_group("morons.group_contributors"):
                view_form_id = self.env.ref('morons.contributor_invoice_view_form_my_po').id
            else:
                view_form_id = self.env.ref('morons.contributor_invoice_view_form_all').id
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "views": [[view_form_id, "form"]],
                "res_id": invoices.id,
                "target": "current",
            }
        else:
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "views": [[self.env.ref('morons.contributor_invoice_view_tree').id, "tree"]],
                "target": "new",
            }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("increment_PO_id")
        res = super(MerctransTask, self).create(vals_list)
        res._send_notyfy_assign_contributor()
        return res

    def write(self, vals):
        res = super(MerctransTask, self).write(vals)
        if vals.get("contributor_id", False) and self._context.get('from_contributor', False):
            self._send_notyfy_assign_contributor()
        return res

    def _send_notyfy_assign_contributor(self):
        # Utility method to send assignation notification upon writing/creation.
        email_template = self.env.ref('morons.email_template_po_assignment', raise_if_not_found=False)
        if not email_template:
            return
        task_model_description = self.env['ir.model']._get(self._name).display_name
        
        email_values = {
            'email_cc': False,
            'auto_delete': True,
            'message_type': 'user_notification',
            'recipient_ids': [],
            'partner_ids': [],
            'scheduled_date': False,
        }
        
        for task in self.sudo():
            if not task.contributor_id:
                continue
            email_values['email_to'] = task.contributor_id.email
            with self.env.cr.savepoint():
                force_send = not(self.env.context.get('import_file', False))
                email_template.send_mail(task.id, force_send=force_send, raise_exception=False, email_values=email_values)
            _logger.info("PO assignment notification sent for user <%s> to <%s>", task.contributor_id.login, task.contributor_id.email)

    def send_email_to_pm(self, send_type=False):
        self.ensure_one()
        email_template = False
        if send_type == 'accepted':
            email_template = self.env.ref('morons.email_template_po_accepted', raise_if_not_found=False)
        elif send_type == 'declined':
            email_template = self.env.ref('morons.email_template_po_declined', raise_if_not_found=False)
        else:
            return
        if not email_template:
            return

        email_values = {
            'email_cc': False,
            'auto_delete': True,
            'message_type': 'user_notification',
            'recipient_ids': [],
            'partner_ids': [],
            'scheduled_date': False,
            'email_to': self.project_id.user_id.email,
        }
        with self.env.cr.savepoint():
            force_send = not(self.env.context.get('import_file', False))
            email_template.send_mail(self.id, force_send=force_send, raise_exception=False, email_values=email_values)

    @api.model
    def _task_message_auto_subscribe_notify(self, users_per_task):
        # Override để không gửi email cho người dùng được assign. chỉ cần gửi cho contributor tại hàm '_send_notyfy_assign_contributor'
        return
