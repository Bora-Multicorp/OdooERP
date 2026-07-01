# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import AccessError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        """
        Override to restrict payment access to KS Payment Access group only.
        This prevents direct URL access even if menu is hidden.
        """
        # Superuser always has access
        if self.env.su:
            return super().check_access_rights(operation, raise_exception)
        
        # Check if user has KS Payment Access group
        has_payment_access = self.env.user.has_group('ks_payment_access_control.group_ks_payment_access')
        
        if not has_payment_access:
            if raise_exception:
                raise AccessError(_(
                    'Access Denied!\n\n'
                    'You do not have permission to access payments.\n'
                    'Only users with "KS Payment Access" rights can access payments.\n\n'
                    'Please contact your administrator to grant you access.'
                ))
            return False
        
        return super().check_access_rights(operation, raise_exception)

    def check_access_rule(self, operation):
        """
        Override to check KS Payment Access group for record-level access.
        This prevents direct URL access to specific payment records.
        """
        if not self.env.su:
            has_payment_access = self.env.user.has_group('ks_payment_access_control.group_ks_payment_access')
            if not has_payment_access:
                raise AccessError(_('You do not have permission to access this payment.'))
        return super().check_access_rule(operation)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to check KS Payment Access group"""
        if not self.env.su:
            has_payment_access = self.env.user.has_group('ks_payment_access_control.group_ks_payment_access')
            if not has_payment_access:
                raise AccessError(_('You do not have permission to create payments.'))
        return super().create(vals_list)

    def write(self, values):
        """Override write to check KS Payment Access group"""
        if not self.env.su:
            has_payment_access = self.env.user.has_group('ks_payment_access_control.group_ks_payment_access')
            if not has_payment_access:
                raise AccessError(_('You do not have permission to modify payments.'))
        return super().write(values)

    def unlink(self):
        """Override unlink to check KS Payment Access group"""
        if not self.env.su:
            has_payment_access = self.env.user.has_group('ks_payment_access_control.group_ks_payment_access')
            if not has_payment_access:
                raise AccessError(_('You do not have permission to delete payments.'))
        return super().unlink()

