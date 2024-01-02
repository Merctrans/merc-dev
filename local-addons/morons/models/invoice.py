# -*- coding: utf-8 -*-

from datetime import timedelta
import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re
import pytz


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
    _description = ''
    _rec_name = 'invoice_id'

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

    invoice_id = fields.Char(string='Invoice ID', 
                             required=True, 
                             copy=False, 
                             readonly=True, 
                             index=True, 
                             default=lambda self: 'New')

    @api.model
    def create(self, vals):
        if vals.get('invoice_id', 'New') == 'New':
            vals['invoice_id'] = self.env['ir.sequence'].next_by_code('morons.invoice') or 'New'
        result = super(Invoice, self).create(vals)
        return result
    
    issue_date = fields.Date(string='Issue Date')
    due_date = fields.Date(string='Due Date', required=True)
    sender = fields.Many2one('res.users', string='Issued By', default=lambda self: self.env.user)

    purchase_order = fields.Many2one('project.task', string='Purchase Order') 
    issued_to = fields.Many2one('res.users', string='Issued To', compute='_compute_issued_to', store=True)

    note = fields.Text(string='Note')

    currency = fields.Many2one(
        'res.currency', 
        string='Currency', 
        compute='_compute_currency',
        required=True,
        store=True
    )

    @api.depends('purchase_order')
    def _compute_issued_to(self):
        for record in self:
            if record.purchase_order and record.purchase_order.user_ids:
                record.issued_to = record.purchase_order.user_ids[0].id
            else:
                record.issued_to = False

    @api.depends('purchase_order')
    def _compute_currency(self):
        for record in self:
            if record:
                record.currency = record.issued_to.currency

    work_unit = fields.Selection(string='Work Unit', 
                                 selection=work_unit_list, 
                                 default='word') 
    
    sale_rate = fields.Float(string="Sale Rate", 
                        digits=(16, 2))
    
    task_volume = fields.Integer(string='Task Volume')

    payable = fields.Monetary(string='Payable', 
                              currency_field='currency', 
                              compute='_compute_payable_amount', 
                              store=True, 
                              readonly=True) 
    
    usd_currency_id = fields.Many2one('res.currency', 
                                      string='USD Currency', 
                                      default=lambda self: self.env.ref('base.USD'))
    
    payable_usd = fields.Monetary(string='Payable(USD)', 
                                  currency_field='usd_currency_id', 
                                  compute='_compute_amount_usd')

    @api.depends('sale_rate', 'task_volume', 'currency')
    def _compute_payable_amount(self):
        for record in self:
            record.payable = record.sale_rate * record.task_volume

    @api.depends('payable')
    def _compute_amount_usd(self):
        """
        For now, it is hardcoded to convert from VND to USD and EUR to USD.
        (TODO) Auto compute regardless of currency.
        """
        for record in self:
            if record.currency.name == 'VND':
                record.payable_usd = record.payable * 0.000041
            elif record.currency.name == 'EUR':
                record.payable_usd = record.payable * 1.10
            else:
                record.payable_usd = record.payable


    status = fields.Selection(string='Status', 
                              selection=invoice_status_list, 
                              default='draft')
    
    payment_status = fields.Many2one(
        'project.task',
        string='Payment Status', 
        compute='_compute_payment_status',
        store=True
    )

    @api.depends('purchase_order')
    def _compute_payment_status(self):
        for record in self:
            if record.purchase_order:
                record.payment_status = record.purchase_order.payment_status
            else:
                record.payment_status = None

class ClientInvoice(models.Model):
    """
    A model representing client invoices in the MercTrans system.

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

    _name = 'morons.client_invoice'
    _description = ''
    _rec_name = 'invoice_id'

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

    invoice_id = fields.Char(string='Invoice ID', 
                             required=True, 
                             copy=False, 
                             readonly=True, 
                             index=True, 
                             default=lambda self: 'New')

    @api.model
    def create(self, vals):
        if vals.get('invoice_id', 'New') == 'New':
            client_name = vals.get('client') and self.env['res.company'].browse(vals['client']).name or ''
            date = fields.Date.today()
            year_month = date.strftime('%Y-%m')

            # Build the base ID
            base_id = f"{client_name} - {year_month}"

            # Search for existing invoices with the same base ID
            existing_ids = self.env['morons.client_invoice'].search([('invoice_id', 'like', f"{base_id}%")])
            count = len(existing_ids)

            # Append the count to the base ID
            new_id = f"{base_id}-{count + 1}" if count else base_id

            vals['invoice_id'] = new_id

        result = super(ClientInvoice, self).create(vals)
        return result
    
    issue_date = fields.Date(string='Issue Date')
    due_date = fields.Date(string='Due Date', required=True)

    client = fields.Many2one('res.company', default=lambda self: self.env.user.company_id, string='Client', required=True)
    customer_reference = fields.Char(string='Customer Reference', required=True)
    address = fields.Text(string='Address')
    email = fields.Char(string='Email')
    sales_order = fields.Many2one('project.task', string='Sales Order')

    @api.constrains('email')
    def validate_email(self):
        for record in self:
            if record.email:
                match = re.match(
                    '^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$',
                    record.email)
                if match is None:
                    raise ValidationError('Not a valid email')

    purchase_order = fields.Many2one('project.task', string='Purchase Order', required=True)
    issued_to = fields.Many2one('res.users', string='Issued To', compute='_compute_issued_to', store=True)

    note = fields.Text(string='Note')

    currency = fields.Many2one(
        'res.currency', 
        string='Currency', 
        compute='_compute_currency',
        required=True,
        store=True
    )

    @api.depends('purchase_order')
    def _compute_issued_to(self):
        for record in self:
            if record.purchase_order and record.purchase_order.user_ids:
                record.issued_to = record.purchase_order.user_ids[0].id
            else:
                record.issued_to = False

    @api.depends('purchase_order')
    def _compute_currency(self):
        for record in self:
            if record:
                record.currency = record.issued_to.currency

    work_unit = fields.Selection(string='Work Unit', 
                                 selection=work_unit_list, 
                                 default='word') 
    
    sale_rate = fields.Float(string="Sale Rate", 
                        digits=(16, 2))
    
    task_volume = fields.Integer(string='Task Volume')

    line_total = fields.Monetary(string='Line Total',
                                    currency_field='currency',
                                    compute='_compute_line_total',
                                    store=True,
                                    readonly=True)
    
    @api.depends('sale_rate', 'task_volume')
    def _compute_line_total(self):
        for record in self:
            record.line_total = record.sale_rate * record.task_volume

    discount = fields.Float(string='Discount')

    @api.model
    def _get_default_discount(self):
        return 0.0

    @api.constrains('discount', 'payable')
    def _check_discount(self):
        for record in self:
            if record.discount > record.payable:
                raise ValidationError("Discount cannot be greater than the total.")
            
    subtotal = fields.Monetary(string='Subtotal',
                                    currency_field='currency',
                                    compute='_compute_subtotal',
                                    store=True,
                                    readonly=True)
    
    @api.depends('line_total', 'discount')
    def _compute_subtotal(self):
        for record in self:
            record.subtotal = record.line_total - record.discount
            
    VAT = fields.Float(string='VAT', default=0.1) 

    payable = fields.Monetary(string='Payable', 
                              currency_field='currency', 
                              compute='_compute_payable_amount', 
                              store=True, 
                              readonly=True)
    
    @api.depends('subtotal', 'VAT')
    def _compute_payable_amount(self):
        for record in self:
            record.payable = record.subtotal * (1 + record.VAT)

    
    usd_currency_id = fields.Many2one('res.currency', 
                                      string='USD Currency', 
                                      default=lambda self: self.env.ref('base.USD'))
    
    payable_usd = fields.Monetary(string='Payable(USD)', 
                                  currency_field='usd_currency_id', 
                                  compute='_compute_amount_usd')

    @api.depends('subtotal', 'VAT')
    def _compute_amount_usd(self):
        """
        For now, it is hardcoded to convert from VND to USD and EUR to USD.
        (TODO) Auto compute regardless of currency.
        """
        for record in self:
            if record.currency.name == 'VND':
                record.payable_usd = record.payable * 0.000041
            elif record.currency.name == 'EUR':
                record.payable_usd = record.payable * 1.10
            else:
                record.payable_usd = record.payable


    status = fields.Selection(string='Status', 
                              selection=invoice_status_list, 
                              default='draft')
    
    payment_status = fields.Selection(
        string='Payment Status', 
        selection=payment_status_list,
        compute='_compute_payment_status',
        store=True
    )