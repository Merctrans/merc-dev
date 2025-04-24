import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import re
import logging
_logger = logging.getLogger(__name__)

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
    _inherit = ["res.users"]

    # Contributor Information
    contributor = fields.Boolean(string='Contributor', default=False)
    currency = fields.Many2one('res.currency', string='Currency')
    skype = fields.Char(string='Skype')
    # bỏ trường nationality, dùng trường nationality_ids thay thế
    nationality = fields.Many2many('res.country', string='Nationality')
    nationality_ids = fields.Many2many('moron.nationality', string='Nationalities')
    country_of_residence = fields.Many2one('res.country')
    my_pos_count = fields.Integer(string='POs Count', compute='_compute_my_pos_count')
    languages_ids = fields.Many2many('res.lang', string='Languages')
    # 1 trường đánh giá ratring từ 0* -> 5* và 1 trường mô tả đánh giá
    rating = fields.Selection([('1', '1*'), ('2', '2*'), ('3', '3*'), ('4', '4*'), ('5', '5*')], 'Rating')
    rating_description = fields.Text(string='Rating Description')

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

    # Purchase Orders
    mertrans_po_ids = fields.One2many('project.task', 'contributor_id', string='Purchase Orders')
    # Invoices
    contributor_invoice_ids = fields.One2many('account.move', 'contributor_id', string='Invoices')
    # Services
    contributor_service_rate_ids = fields.One2many('contributor.service.rate', 'contributor_id', string='Service Rates')

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
        contributor_group_users = contributor_group.with_context(active_test=False).users
        add_users = contributors - contributor_group_users
        if add_users:
            add_users.write({'groups_id': [(4, contributor_group.id)]})

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + CONTRIBUTOR_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + CONTRIBUTOR_FIELDS

    def action_reset_password(self):
        """ create signup token for each user, and send their signup url by email """
        if self.env.context.get('install_mode', False):
            return
        if self.filtered(lambda user: not user.active):
            raise UserError(_("You cannot perform this action on an archived user."))
        # prepare reset password signup
        create_mode = bool(self.env.context.get('create_user'))

        # no time limit for initial invitation, only for reset password
        expiration = False if create_mode else now(days=+1)

        self.mapped('partner_id').signup_prepare(signup_type="reset", expiration=expiration)

        # send email to users with their signup url
        user_template = False
        contributor_template = False
        if create_mode:
            try:
                user_template = self.env.ref('auth_signup.set_password_email', raise_if_not_found=False)
                contributor_template = self.env.ref('morons.email_template_new_contributor', raise_if_not_found=False)
            except ValueError:
                pass
        if not user_template:
            user_template = self.env.ref('auth_signup.reset_password_email')
        if not contributor_template:
            contributor_template = self.env.ref('auth_signup.reset_password_email')
        
        assert user_template._name == 'mail.template'
        assert contributor_template._name == 'mail.template'

        email_values = {
            'email_cc': False,
            'auto_delete': True,
            'message_type': 'user_notification',
            'recipient_ids': [],
            'partner_ids': [],
            'scheduled_date': False,
        }

        for user in self:
            if not user.email:
                raise UserError(_("Cannot send email: user %s has no email address.", user.name))
            email_values['email_to'] = user.email
            # TDE FIXME: make this template technical (qweb)
            template = user_template if not user.contributor else contributor_template
            with self.env.cr.savepoint():
                force_send = not(self.env.context.get('import_file', False))
                template.send_mail(user.id, force_send=force_send, raise_exception=True, email_values=email_values)
            _logger.info("Password reset email sent for user <%s> to <%s>", user.login, user.email)
