from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class MoronSaleOrder(models.Model):
    _name = "moron.sale.order"
    _description = "Sale Order"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Name', default='New', readonly=True, required=True, tracking=True)
    project_id = fields.Many2one('project.project', string='Project', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True,
        domain=[('type', '=', 'contact'),('customer_rank', '>', 0)], tracking=True)
    partner_invoice_id = fields.Many2one('res.partner', 'Invoice Address',
                                        compute='_compute_partner_invoice_id', store=True, precompute=True, tracking=True)

    company_id = fields.Many2one(related='project_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  compute='_compute_currency_id', store=True, readonly=False, tracking=True)
    tag_report_id = fields.Many2one('project.tags', string='Tag Report',
                                    compute='_compute_tag_report_id', store=True, readonly=False, tracking=True)

    date_order = fields.Date(string='Order Date', default=fields.Date.context_today, tracking=True)
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', tracking=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('invoiced', 'Invoiced'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')], string='Status', default='draft',
        compute='_compute_status', store=True, readonly=False, tracking=True)

    line_ids = fields.One2many('moron.sale.order.line', 'sale_order_id', string='Lines')
    client_invoice_id = fields.Many2one('account.move', string='Client Invoice', tracking=True)

    amount = fields.Monetary(string='Amount', compute='_compute_amount', store=True, currency_field='currency_id', tracking=True)
    currency_company_id = fields.Many2one('res.currency', compute='_compute_amount_same_currency_company', store=True)
    amount_same_currency_company = fields.Monetary(string='Amount (by company currency)',
                              compute='_compute_amount_same_currency_company', store=True,
                              currency_field='currency_company_id')

    @api.constrains('project_id')
    def _check_project_id(self):
        for r in self:
            if r.project_id and (r.project_id.moron_sale_order_ids - r).exists():
                raise ValidationError(_("Each project can only have 1 Sale order: %s") % r.project_id.name)

    @api.depends('partner_id')
    def _compute_partner_invoice_id(self):
        """
        Compute the invoice address of the partner
        """
        for r in self:
            r.partner_invoice_id = r.partner_id.address_get(['invoice'])['invoice'] if r.partner_id else False

    @api.depends('project_id')
    def _compute_currency_id(self):
        for r in self:
            r.currency_id = r.project_id.currency_id

    @api.depends('client_invoice_id', 'client_invoice_id.state', 'client_invoice_id.payment_state')
    def _compute_status(self):
        for r in self:
            if r.client_invoice_id.payment_state == 'paid' and r.client_invoice_id.state == 'posted':
                r.status = 'completed'
            elif r.client_invoice_id.state in ['draft', 'posted']:
                r.status = 'invoiced'
            elif r.client_invoice_id.state == 'cancel':
                r.status = 'cancelled'
            else:
                r.status = 'draft'

    @api.depends('project_id')
    def _compute_tag_report_id(self):
        for r in self:
            r.tag_report_id = r.project_id.tag_ids[:1]

    @api.depends('line_ids', 'line_ids.project_value')
    def _compute_amount(self):
        for r in self:
            amount = sum(r.line_ids.mapped('project_value'))
            r.amount = amount

    @api.depends('company_id', 'currency_id', 'amount')
    def _compute_amount_same_currency_company(self):
        for r in self:
            r.currency_company_id = r.company_id.currency_id or self.env.company
            if r.currency_id == r.currency_company_id:
                r.amount_same_currency_company = r.amount
            elif r.currency_id and r.currency_company_id:
                # đổi tiền tệ từ currency_id sang currency_company_id
                new_amount = r.currency_id._convert(
                            r.amount,
                            r.currency_company_id,
                            r.company_id,
                            fields.Date.context_today(r)
                        )
                r.amount_same_currency_company = new_amount

    @api.onchange('project_id')
    def onchange_project_id(self):
        """
        Thiết lập lại partner, SO lines
        """
        if self.project_id:
            project = self.project_id
            self.write({
                'partner_id': project.partner_id,
                'line_ids': [(5, 0, 0), (0, 0, {'name': project.name, 'volume': project.volume, 'sale_rate': project.sale_rate, 'work_unit': project.work_unit})]
            })
        else:
            self.write({'partner_id': False, 'line_ids': [(5, 0, 0)]})

    @api.model_create_multi
    def create(self, vals_list):
        """
        Ghi đè hàm create để tạo sequence tự động cho trường name
        với format SOxxxxx
        """
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('moron.sale.order') or 'New'
        return super().create(vals_list)

    def action_create_invoice(self):
        """
        Cho phép tạo invoice cho 1 hoặc nhiều SO:
        - Nếu SO đã có invoice => cảnh báo
        - Nếu SO không có invoice => tạo invoice:
            - Tạo invoice gộp cho nhiều SO nếu có nhiều SO
        """
        # check permission
        if not self.env.user.has_group("morons.group_pm") and not self.env.user.has_group("morons.group_bod"):
            raise ValidationError(_("You cannot create a customer invoice, please contact PM, BoD."))

        # check common
        for r in self:
            if not r.partner_id:
                raise ValidationError("A customer must be designated for sale order '%s'." % r.name)
            if r.client_invoice_id:
                raise ValidationError(_("This sale order '%s' already has an invoice.") % r.name)

        invoices = self.env["account.move"]
        for partner in self.partner_id:
            AccountMove = self.env["account.move"]
            # check partner
            sale_orders = self.filtered(lambda so: so.partner_id == partner)
            if len(sale_orders.currency_id) > 1:
                raise ValidationError(_("You cannot create an invoice for multiple currencies: %s") % sale_orders.mapped("name"))
            
            invoice_line_data = []
            for so in sale_orders:
                for line in so.line_ids:
                    invoice_line_data.append((0, 0, {
                        'name': "%s - %s" % (line.name, so.name),
                        'quantity': line.volume,
                        'price_unit': line.sale_rate,
                        'tax_ids': False
                    }))
            
            invoice = AccountMove.create({
                'partner_id': partner.id,
                'move_type': 'out_invoice',
                'currency_id': sale_orders.currency_id.id,
                'invoice_date': fields.Date.context_today(self),
                'invoice_payment_term_id': sale_orders.payment_term_id[:1].id,
                'invoice_line_ids': invoice_line_data
            })
            if invoice:
                sale_orders.sudo().write({"client_invoice_id": invoice.id})
                invoices |= invoice


        if len(invoices) == 1:
            view_form_id = self.env.ref('morons.client_invoice_view_form_all').id
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
                "views": [[self.env.ref('morons.client_invoice_view_tree').id, "tree"]],
                "target": "new",
            }

    def action_cancel(self):
        self.write({'status': 'cancelled'})

    def action_draft(self):
        self.write({'status': 'draft'})
