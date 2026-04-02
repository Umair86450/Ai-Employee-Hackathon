from odoo import models
from odoo.exceptions import AccessError


class NoDeleteGuardMixin(models.AbstractModel):
    _name = "ai.employee.no.delete.guard.mixin"
    _description = "Guard unlink for selected accounting records"

    def unlink(self):
        if self.env.user.has_group("ai_employee_accounting_guard.group_accounting_no_delete"):
            raise AccessError("Delete is blocked for this user.")
        return super().unlink()


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "ai.employee.no.delete.guard.mixin"]


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ["account.move.line", "ai.employee.no.delete.guard.mixin"]


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = ["account.payment", "ai.employee.no.delete.guard.mixin"]


class AccountJournal(models.Model):
    _name = "account.journal"
    _inherit = ["account.journal", "ai.employee.no.delete.guard.mixin"]


class AccountAccount(models.Model):
    _name = "account.account"
    _inherit = ["account.account", "ai.employee.no.delete.guard.mixin"]


class AccountTax(models.Model):
    _name = "account.tax"
    _inherit = ["account.tax", "ai.employee.no.delete.guard.mixin"]


class AccountPaymentTerm(models.Model):
    _name = "account.payment.term"
    _inherit = ["account.payment.term", "ai.employee.no.delete.guard.mixin"]


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "ai.employee.no.delete.guard.mixin"]


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "ai.employee.no.delete.guard.mixin"]


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "ai.employee.no.delete.guard.mixin"]
