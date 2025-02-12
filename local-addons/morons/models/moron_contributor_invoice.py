from odoo import models, fields, api


class MercTransContributorInvoice(models.Model):
    _inherit = "account.move"

    purchase_order_ids = fields.One2many("project.task", 'contributor_invoice_id', string="Purchase Orders")
    is_contributor_invoice = fields.Boolean(string="Is Contributor Invoice", compute="_compute_is_contributor_invoice", store=True,
                                            help="Trường kỹ thuật, dùng để phân quyền")
    amount_total_signed_display = fields.Monetary(string='Invoice Total',
                                                    compute='_compute_amount_total_signed_display',
                                                    currency_field='company_currency_id')

    # Các trường kỹ thuật, tham chiếu giữa hóa đơn và payment để chỉnh sửa payment tự động thông qua hóa đơn
    moron_contributor_payment_ids = fields.One2many("account.payment", 'moron_contributor_invoice_id', string="Contributor Payments")

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
            self.moron_contributor_payment_ids.unlink()
        return res

    def button_cancel(self):
        res = super(MercTransContributorInvoice, self).button_cancel()
        if self.moron_contributor_payment_ids:
            self.moron_contributor_payment_ids.filtered(lambda x: x.state == "posted").action_draft()
            self.moron_contributor_payment_ids.unlink()
        return res
