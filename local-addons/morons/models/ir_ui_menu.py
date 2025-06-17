from odoo import models, api, tools


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        """
        Nếu là Accountan, PM, BoD thì ẩn menu của contributor
        """
        res = super()._load_menus_blacklist()
        if self.env.user.has_group('morons.group_accountants'):
            res.append(self.env.ref('morons.my_pos_menu').id)
            res.append(self.env.ref('morons.my_invoices_menu').id)
        return res
