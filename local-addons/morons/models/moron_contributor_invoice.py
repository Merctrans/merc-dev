from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MercTransContributorInvoice(models.Model):
    _inherit = "account.move"

    # contributor
    contributor_id = fields.Many2one("res.users", string='Contributor',
                                        compute="_compute_contributor_id", store=True)
    purchase_order_ids = fields.One2many("project.task", 'contributor_invoice_id', string="Purchase Orders",
                                        domain="[('contributor_id.partner_id', '=', partner_id), ('contributor_invoice_id', '=', False)]")
    PO_str = fields.Char(string="Purchase Orders", compute="_compute_PO_str", compute_sudo=True)
    is_contributor_invoice = fields.Boolean(string="Is Contributor Invoice", compute="_compute_is_contributor_invoice", store=True,
                                            help="Trường kỹ thuật, dùng để phân quyền")
    amount_total_signed_display = fields.Monetary(string='Invoice Total',
                                                    compute='_compute_amount_total_signed_display',
                                                    currency_field='company_currency_id')

    # Các trường kỹ thuật, tham chiếu giữa hóa đơn và payment để chỉnh sửa payment tự động thông qua hóa đơn
    moron_contributor_payment_ids = fields.One2many("account.payment", 'moron_contributor_invoice_id', string="Contributor Payments")

    # Override
    invoice_date = fields.Date(default=fields.Date.context_today, string='Invoice Date')

    @api.depends("purchase_order_ids")
    def _compute_contributor_id(self):
        for r in self:
            r.contributor_id = r.purchase_order_ids[:1].contributor_id

    @api.depends("purchase_order_ids")
    def _compute_is_contributor_invoice(self):
        for invoice in self:
            if invoice.purchase_order_ids:
                invoice.is_contributor_invoice = True
            else:
                invoice.is_contributor_invoice = False

    @api.depends('amount_total_signed')
    def _compute_amount_total_signed_display(self):
        """
        Theo logic Odoo: Hóa đơn của Contributor về mặt kế toán sẽ mang số tiền âm (Hóa đơn nhà cung cấp)
        - Nên cần hiển thị số tiền dương để người dùng dễ nhìn.
        - Trường hợp muốn nhìn chuẩn theo mặt kế toán. hãy hiện thị trường `amount_total_signed`
        """
        for r in self:
            r.amount_total_signed_display = abs(r.amount_total_signed)

    @api.onchange("partner_id")
    def onchange_partner_id(self):
        if self.partner_id and not self.purchase_order_ids:
            self.currency_id = self.partner_id.user_ids[:1].currency

    @api.onchange("purchase_order_ids")
    def onchange_purchase_order_ids(self):
        if self.purchase_order_ids:
            # check po cùng contributor
            if len(self.purchase_order_ids.contributor_id) > 1:
                raise UserError(_("Purchase Orders has multiple contributors"))
            # check cùng tiền tệ
            if len(self.purchase_order_ids.currency_id) > 1:
                raise UserError(_("Purchase Orders has multiple currencies"))
            # duyệt qua PO để tạo invoice
            lines_data = [(6, 0, [])]
            for po in self.purchase_order_ids:
                # tạo invoice line
                lines_data.append((0, 0, {
                    'name': po.name,
                    'quantity': po.volume,
                    'price_unit': po.rate,
                    'tax_ids': False
                }))
            self.invoice_line_ids = lines_data
            self.currency_id = self.purchase_order_ids.currency_id
        else:
            self.invoice_line_ids = False

    @api.depends("purchase_order_ids")
    def _compute_PO_str(self):
        for r in self:
            r.PO_str = ", ".join([po.name for po in r.purchase_order_ids])

    def action_register_payment(self):
        """
        Truyền giá trị mặc định, để payment nhận diện đc là đang thanh toán cho hóa đơn này
        Đối với Moron chỉ có thanh toán cho 1 hóa đơn khi dùng tính năng 'register payment'
        """
        if self.moron_contributor_payment_ids:
            # Xóa các payment nếu đã có để tạo lại payment mới
            self.moron_contributor_payment_ids.filtered(lambda x: x.state == "posted").action_draft()
            self.moron_contributor_payment_ids.unlink()
        res = super().action_register_payment()
        if len(self) == 1:
            res["context"]["default_moron_contributor_invoice_id"] = self.id
        return res

    def button_draft(self):
        res = super(MercTransContributorInvoice, self).button_draft()
        if self.moron_contributor_payment_ids:
            # Xóa các payment nếu đã có để tạo lại payment mới
            self.moron_contributor_payment_ids.filtered(lambda x: x.state == "posted").action_draft()
            self.moron_contributor_payment_ids.sudo().unlink()
        return res

    def button_cancel(self):
        res = super(MercTransContributorInvoice, self).button_cancel()
        if self.moron_contributor_payment_ids:
            self.moron_contributor_payment_ids.filtered(lambda x: x.state == "posted").action_draft()
            self.moron_contributor_payment_ids.sudo().unlink()
        return res

    # Override invoice. Include customer invoice, contributor invoice
    def _post(self, soft=True):
        self_sudo = self
        if self.user_has_groups('morons.group_bod,morons.group_pm,morons.group_accountants'):
            self_sudo = self.sudo()
        return super(MercTransContributorInvoice, self_sudo)._post(soft)

    def button_draft(self):
        self_sudo = self
        if self.user_has_groups('morons.group_bod,morons.group_pm,morons.group_accountants'):
            self_sudo = self.sudo()
        return super(MercTransContributorInvoice, self_sudo).button_draft()

    def action_send_invoice_to_contributor(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('morons.email_template_contributor_invoice', raise_if_not_found=False)
        lang = False
        if template:
            lang = template._render_lang(self.ids)[self.id]
        if not lang:
            lang = get_lang(self.env).code
        compose_form = self.env.ref('account.account_invoice_send_wizard_form', raise_if_not_found=False)
        ctx = dict(
            default_model='account.move',
            default_res_id=self.id,
            default_res_model='account.move',
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            default_email_layout_xmlid="mail.mail_notification_layout_with_responsible_signature",
            model_description=self.with_context(lang=lang).type_name,
            force_email=True,
            active_ids=self.ids,
        )

        report_action = {
            'name': _('Send Invoice'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.send',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

        if self.env.is_admin() and not self.env.company.external_report_layout_id and not self.env.context.get('discard_logo_check'):
            return self.env['ir.actions.report']._action_configure_external_report_layout(report_action)

        return report_action
