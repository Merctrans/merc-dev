import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re
import pytz


# uncomment and create a view for it
class InternalUser(models.Model):
    """
    Model for managing internal users at MercTrans.

    This class extends 'res.users' in Odoo, tailored for MercTrans needs.
    It stores user roles, contact info, nationality, payment methods, and education.

    Attributes:
        General:
            _inherit (str): Inherited res.users.
            contributor (fields.Boolean): User's contributor status.
            active (fields.Boolean): User account status.
            currency (fields.Many2one): User's preferred currency.
            skype (fields.Char): User's Skype ID.
            nationality (fields.Many2many): User's nationality.
            country_of_residence (fields.Many2one): User's country of residence.
            timezone (fields.Selection): User's timezone.

        Payment Methods:
            paypal (fields.Char): User's PayPal ID.
            transferwise_id (fields.Char): User's Wise ID.
            bank_account_number (fields.Char): User's bank account number.
            bank_name (fields.Char): User's bank name.
            iban (fields.Char): User's IBAN.
            swift (fields.Char): User's SWIFT code.
            bank_address (fields.Char): User's bank address.
            preferred_payment_method (fields.Selection): User's preferred payment method.

        Education and Experience:
            dates_attended (fields.Date): Dates attended educational institutions.
            school (fields.Char): School name.
            field_of_study (fields.Char): User's field of study.
            year_obtained (fields.Selection): Year user obtained their degree.
            certificate (fields.Char): Certificate name.

        Other Field:
            assigned_records_count (fields.Integer): Number of assigned tasks computed for the user.

    Methods:
        _tz_get(): Returns all timezones for the timezone selection field.
        validate_email(): Validates email format for PayPal and login.
    """

    _inherit = ["res.users"]

    contributor = fields.Boolean(string='Contributor', default=False)
    active = fields.Boolean(string='Active', default=True)
    currency = fields.Many2one('res.currency', string='Currency', required=True)
    skype = fields.Char(string='Skype')
    nationality = fields.Many2many('res.lang', required=True)
    country_of_residence = fields.Many2one('res.country')
    timezone = fields.Selection('_tz_get',
                                string='Timezone',
                                required=True,
                                default=lambda self: self.env.user.tz or 'UTC')
    
    @api.model
    def _tz_get(self):
        return [(x, x) for x in pytz.all_timezones]
    
    # Payment Methods
    paypal = fields.Char('PayPal ID')
    transferwise_id = fields.Char('Wise ID')
    bank_account_number = fields.Char('Bank Account Number')
    bank_name = fields.Char('Bank Name')
    iban = fields.Char('IBAN')
    swift = fields.Char('SWIFT')
    bank_address = fields.Char('Bank Address')
    preferred_payment_method = fields.Selection(selection=[('paypal', 'Paypal'),
                                                           ('transferwise', 'Wise'),
                                                           ('bank', 'Bank Transfer')])
    
    @api.constrains('paypal')
    def validate_paypal(self):
        if self.paypal:
            match = re.match(
                '^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$',
                self.paypal)
            if match is None:
                raise ValidationError('Not a valid email')
    
    # Education and Experience
    dates_attended = fields.Date('Date Attended')
    school = fields.Char('School')
    field_of_study = fields.Char('Field of Study')
    year_obtained = fields.Selection([(str(num), str(num)) for num in range(1900, datetime.datetime.now().year + 1)], 'Year')
    certificate = fields.Char('Certificate')
    
    assigned_records_count = fields.Integer(string=' Assigned Tasks', compute='_compute_assigned_records_count')

    def _compute_assigned_records_count(self):
        for record in self:
            # Count the number of project.task records where this user is in user_ids
            count = self.env['project.task'].search_count([('user_ids', 'in', record.id)])
            record.assigned_records_count = count
    
    @api.constrains('login')
    def validate_login(self):
        if self.login:
            match = re.match(
                '^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$',
                self.login)
            if match is None:
                raise ValidationError('Not a valid email')
