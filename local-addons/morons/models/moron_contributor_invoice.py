from odoo import models, fields, api


class MercTransContributorInvoice(models.Model):
    _inherit = "account.move"

    purchase_order_ids = fields.One2many("project.task", 'contributor_invoice_id', string="Purchase Orders")
    is_contributor_invoice = fields.Boolean(string="Is Contributor Invoice", compute="_compute_is_contributor_invoice", store=True,
                                            help="Trường kỹ thuật, dùng để phân quyền")
    amount_total_signed_display = fields.Monetary(string='Invoice Total',
                                                    compute='_compute_amount_total_signed_display',
                                                    currency_field='company_currency_id')

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
