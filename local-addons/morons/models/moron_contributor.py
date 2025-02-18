import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


CONTRIBUTOR_FIELDS = [
    'login',
    'phone',
    'skype',
    'nationality',
    'country_of_residence',
    'currency',
    'vat',
    'tz',
    'preferred_payment_method',
    'paypal',
    'transferwise_id',
    'bank_account_number',
    'bank_name',
    'iban',
    'swift',
    'bank_address',
]


class InternalUser(models.Model):
    """
    A model for managing internal users at MercTrans.

    This class extends the 'res.users' model from Odoo, specifically tailored for 
    the needs of MercTrans. It includes additional fields to store information 
    about the users' roles, contact details, nationality, payment methods, and 
    educational background. This class is crucial for managing internal users' 
    data, from basic identification details to more specific information like 
    payment methods and educational qualifications.

    Attributes:
        General:
            _inherit (str): Inherited model name in the Odoo framework.
            contributor (fields.Boolean): Field to indicate if the user is a contributor.
            active (fields.Boolean): Field to indicate if the user account is active.
            currency (fields.Many2one): Relation to 'res.currency' to set the user's preferred currency.
            skype (fields.Char): Field for the user's Skype ID.
            nationality (fields.Many2many): Relation to 'res.lang' to represent the user's nationality.
            country_of_residence (fields.Many2one): Relation to 'res.country' for the user's country of residence.
            timezone (fields.Selection): Selection field for the user's timezone.

        Payment Methods:
            paypal (fields.Char): Field for the user's PayPal ID.
            transferwise_id (fields.Char): Field for the user's Wise ID.
            bank_account_number (fields.Char): Field for the user's bank account number.
            bank_name (fields.Char): Field for the name of the user's bank.
            iban (fields.Char): Field for the user's IBAN.
            swift (fields.Char): Field for the user's SWIFT code.
            bank_address (fields.Char): Field for the user's bank address.
            preferred_payment_method (fields.Selection): Selection field for the user's preferred payment method.

        Education and Experience:
            dates_attended (fields.Date): Field for the dates the user attended educational institutions.
            school (fields.Char): Field for the name of the school the user attended.
            field_of_study (fields.Char): Field for the user's field of study.
            year_obtained (fields.Selection): Selection field for the year the user obtained their degree.
            certificate (fields.Char): Field for the name of any certificate obtained by the user.

    Methods:
        validate_email(): Validates the format of the user's email for PayPal and login.
    """

    _inherit = ["res.users"]

    # Contributor Information
    contributor = fields.Boolean(string='Contributor', default=False)
    currency = fields.Many2one('res.currency', string='Currency')
    skype = fields.Char(string='Skype')
    nationality = fields.Many2many('res.country')
    country_of_residence = fields.Many2one('res.country')
    my_pos_count = fields.Integer(string='POs Count', compute='_compute_my_pos_count')

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
    # Education and Experience
    dates_attended = fields.Date('Date Attended')
    school = fields.Char('School')
    field_of_study = fields.Char('Field of Study')
    year_obtained = fields.Selection([(str(num), str(num)) for num in range(1900, datetime.datetime.now().year + 1)], 'Year')
    certificate = fields.Char('Certificate')

    @api.constrains('paypal')
    def validate_paypal(self):
        if self.paypal:
            match = re.match(
                '^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$',
                self.paypal)
            if match is None:
                raise ValidationError(_('Not a valid email'))

    @api.constrains('login')
    def validate_login(self):
        if self.login:
            match = re.match(
                '^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$',
                self.login)
            if match is None:
                raise ValidationError(_('Not a valid email'))

    def _compute_my_pos_count(self):
        for r in self:
            r.my_pos_count = len(r.task_ids)

    @api.model_create_multi
    def create(self, vals_list):
        self_sudo = self
        if self.user_has_groups('morons.group_bod,morons.group_pm'):
            self_sudo = self.sudo()
        res = super(InternalUser, self_sudo).create(vals_list)
        res._update_is_contributor()
        return res

    def write(self, vals):
        self_sudo = self
        if self.user_has_groups('morons.group_bod,morons.group_pm'):
            self_sudo = self.sudo()
        res = super(InternalUser, self_sudo).write(vals)
        self._update_is_contributor()
        return res

    def _update_is_contributor(self):
        """
        Nếu đánh dấu là contributor thì add users vào contributor group.
        """
        contributors = self.filtered(lambda r: r.contributor)
        contributor_group = self.env.ref('morons.group_contributors')
        contributor_group_users = contributor_group.users
        add_users = contributors - contributor_group_users
        if add_users:
            add_users.write({'groups_id': [(4, contributor_group.id)]})

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + CONTRIBUTOR_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + CONTRIBUTOR_FIELDS
