# -*- coding: utf-8 -*-

from odoo import models, fields, api
import requests

YOUR_API_KEY = 'fdb0f4d94e1ba8d6d9e3bb01e4dd6472'

class Invoice(models.Model):
    """
    A model representing invoices in the MercTrans system.

    This class extends the basic functionality of Odoo's invoicing system 
    to meet the specific requirements of MercTrans. It includes features 
    like a variety of work units, different statuses for invoices and payments, 
    and the capability to handle different currencies with automatic conversion 
    to USD. It also manages the link with purchase orders from projects and 
    calculates payable amounts based on dynamic rates and units.

    Attributes:
        _name (str): Identifier for the Odoo model.
        invoice_status_list (list of tuples): A predefined list of possible statuses for an invoice.
        work_unit_list (list of tuples): A predefined list of work units applicable to an invoice.
        payment_status_list (list of tuples): A predefined list of payment statuses for tracking invoice payments.
        issue_date (fields.Date): Field for the date when the invoice is issued.
        due_date (fields.Date): Field for the date when the invoice payment is due.
        sender (fields.Char): Field for the name of the sender of the invoice.
        purchase_order (fields.Many2one): Relationship to the 'project.project' model, representing the associated purchase order.
        purchase_order_name (fields.Char): Field for displaying the name of the related purchase order, derived from 'purchase_order'.
        note (fields.Text): Field for any additional notes or comments on the invoice.
        currency (fields.Many2one): Field linking to the 'res.currency' model for specifying the currency used in the invoice.
        work_unit (fields.Selection): Field for selecting a work unit from the work_unit_list.
        rate (fields.Float): Field for the rate applied in the invoice, dependent on the chosen work unit.
        sale_unit (fields.Integer): Field for the number of work units being billed in the invoice.
        payable (fields.Monetary): Computed field for the total payable amount in the invoice's currency.
        payable_usd (fields.Monetary): Computed field for the total payable amount converted to USD.
        status (fields.Selection): Field for the current status of the invoice, selected from invoice_status_list.
        payment_status (fields.Selection): Field for the current payment status of the invoice, selected from payment_status_list.

    Methods:
        _compute_payable_amount(self): Computes the total payable amount based on the rate and sale unit.
        _compute_amount_usd(self): Converts the payable amount into USD based on the current exchange rate and invoice date.
    """

    _name = 'morons.invoice'

    invoice_status_list = [
        ("in progress", "In Progress"),
        ("completed", "Completed"),
        ("canceled", "Canceled"),
        ("draft", "Draft"),
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

    invoice_id = fields.Char(string='Invoice ID', required=True, copy=False, readonly=True, index=True, default=lambda self: 'New')

    @api.model
    def create(self, vals):
        if vals.get('invoice_id', 'New') == 'New':
            vals['invoice_id'] = self.env['ir.sequence'].next_by_code('morons.invoice') or 'New'
        result = super(Invoice, self).create(vals)
        return result
    
    issue_date = fields.Date(string='Issue Date')
    due_date = fields.Date(string='Due Date')
    sender = fields.Many2one('res.user',string='Issued By') 

    purchase_order = fields.Many2one('project.task',
                    string='Purchase Order',
                    domain=lambda self: self._get_purchase_order_domain())

    def _get_purchase_order_domain(self):
        if self.env.user.has_group('base.group_system') or self.env.user.has_group('morons.group_bod') or self.env.user.has_group('morons.group_accountants'):
            return []
        elif self.env.user.has_group('morons.group_pm'):
            accountant_users = self.env['res.users'].search([('groups_id', '=', self.env.ref('morons.group_accountants').id)])
            accountant_user_ids = accountant_users.mapped('id')
            return [('user_ids', 'not in', accountant_user_ids)]
        else:
            return [('user_ids', '=', self.env.uid)]

    # purchase_order_name = fields.Char(string="Purchase Order Name", related='purchase_order.name', readonly=True)


    note = fields.Text(string='Note')

    currency = fields.Many2one('res.currency', string='Currency')
    work_unit = fields.Selection(string='Work Unit', selection=work_unit_list, default='word') 
    rate = fields.Float(string="Rate", digits=(16, 2))
    sale_unit = fields.Integer(string='Sale Unit')
    payable = fields.Monetary(string='Payable', currency_field='currency', compute='_compute_payable_amount', store=True, readonly=True)
    usd_currency_id = fields.Many2one('res.currency', string='USD Currency', default=lambda self: self.env.ref('base.USD'))
    payable_usd = fields.Monetary(string='Payable(USD)', currency_field='usd_currency_id', compute='_compute_amount_usd')

    @api.depends('rate', 'sale_unit')
    def _compute_payable_amount(self):
        for record in self:
            record.payable = record.rate * record.sale_unit

    @api.depends('payable', 'currency')
    def _compute_amount_usd(self):
        """
        Converts the payable amount into USD based on the current exchange rate.
        """
        for record in self:
            if record.currency.name == 'USD':
                record.payable_usd = record.payable
            else:
                # Construct the API URL
                api_url = f"https://api.exchangeratesapi.io/v1/latest?access_key={YOUR_API_KEY}&base={record.currency.name}&symbols=USD"
                
                try:
                    response = requests.get(api_url)
                    response.raise_for_status()  # Raises a HTTPError if the response status code is 4XX/5XX
                    data = response.json()
                    
                    # Check if the request was successful and USD rate is available
                    if data.get('success') and 'rates' in data and 'USD' in data['rates']:
                        usd_rate = data['rates']['USD']
                        record.payable_usd = record.payable * usd_rate
                    else:
                        record.payable_usd = 0  # Consider how you want to handle errors or missing rates
                except requests.RequestException as e:
                    record.payable_usd = 0
                    raise e


    # @api.depends('payable', 'currency')
    # def _compute_payable_usd(self):
    #     for record in self:
    #         USD = self.env['res.currency'].search([('name', '=', 'USD')])
    #         curr = self.env['res.currency'].search([('name', '=', 'VND')])
    #         record.payable_usd = USD.compute(record.payable, curr)

    status = fields.Selection(string='Status', selection=invoice_status_list, default='draft')
    payment_status = fields.Selection(string='Payment Status', selection=payment_status_list, default='unpaid')

