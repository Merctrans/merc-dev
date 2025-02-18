from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MercTransClientInvoice(models.Model):
    _inherit = "account.move"
    
    sale_order_ids = fields.One2many("moron.sale.order", 'client_invoice_id', string="Sale Orders",
                                    domain="[('partner_id', '=', partner_id), ('client_invoice_id', '=', False)]")
    moron_project_ids = fields.Many2many("project.project", string="Projects",
                                        compute="_compute_moron_project_ids")
    is_client_invoice = fields.Boolean(string="Is Client Invoice", compute="_compute_is_client_invoice", store=True,
                                            help="Trường kỹ thuật, dùng để phân quyền")

    paid_on = fields.Date(string="Paid On",
                         compute="_compute_paid_on", store=True, readonly=False, tracking=True)

    # Các trường kỹ thuật, tham chiếu giữa hóa đơn và payment để chỉnh sửa payment tự động thông qua hóa đơn
    moron_client_payment_ids = fields.One2many("account.payment", 'moron_client_invoice_id', string="Client Payments")

    @api.depends("sale_order_ids")
    def _compute_is_client_invoice(self):
        for invoice in self:
            if invoice.sale_order_ids:
                invoice.is_client_invoice = True
            else:
                invoice.is_client_invoice = False

    @api.depends("moron_client_payment_ids", 'payment_state')
    def _compute_paid_on(self):
        for r in self:
            payments_done = r.moron_client_payment_ids.filtered(lambda x: x.state == "posted")
            if payments_done and r.payment_state == "paid":
                payment_date_list = payments_done.mapped("date")
                r.paid_on = max(payment_date_list) if payment_date_list else False
            else:
                r.paid_on = False

    @api.depends("sale_order_ids")
    def _compute_moron_project_ids(self):
        for r in self:
            r.moron_project_ids = r.sale_order_ids.project_id

    @api.onchange("sale_order_ids")
    def onchange_sale_order_ids(self):
        if self.sale_order_ids:
            # check so cùng partner
            if len(self.sale_order_ids.partner_id) > 1:
                raise UserError(_("Sale Orders has multiple partners"))
            # check cùng tiền tệ
            if len(self.sale_order_ids.currency_id) > 1:
                raise UserError(_("Sale Orders has multiple currencies"))
            
            # Duyệt qua SO để tạo invoice
            lines_data = [(6, 0, [])]
            for so in self.sale_order_ids:
                for line in so.line_ids:
                    lines_data.append((0, 0, {
                        'name': line.name,
                        'quantity': line.volume,
                        'price_unit': line.sale_rate,
                        'tax_ids': False
                    }))
            self.invoice_line_ids = lines_data
            self.currency_id = self.sale_order_ids.currency_id
        else:
            self.invoice_line_ids = False

    def action_register_payment(self):
        """
        Truyền giá trị mặc định, để payment nhận diện đc là đang thanh toán cho hóa đơn này
        Đối với Moron chỉ có thanh toán cho 1 hóa đơn khi dùng tính năng 'register payment'
        """
        if self.moron_client_payment_ids:
            # Xóa các payment nếu đã có để tạo lại payment mới
            self.moron_client_payment_ids.filtered(lambda x: x.state == "posted").action_draft()
            self.moron_client_payment_ids.unlink()
        res = super().action_register_payment()
        if len(self) == 1:
            res["context"]["default_moron_client_invoice_id"] = self.id
        return res

    def button_draft(self):
        res = super(MercTransClientInvoice, self).button_draft()
        if self.moron_client_payment_ids:
            # Xóa các payment nếu đã có để tạo lại payment mới
            self.moron_client_payment_ids.filtered(lambda x: x.state == "posted").action_draft()
            self.moron_client_payment_ids.sudo().unlink()
        return res

    def button_cancel(self):
        res = super(MercTransClientInvoice, self).button_cancel()
        if self.moron_client_payment_ids:
            self.moron_client_payment_ids.filtered(lambda x: x.state == "posted").action_draft()
            self.moron_client_payment_ids.sudo().unlink()
        return res
