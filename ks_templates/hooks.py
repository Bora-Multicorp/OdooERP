# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Hide the standard 'PDF' (account_invoices) from the invoice Download menu."""
    report = env.ref('account.account_invoices', raise_if_not_found=False)
    if report:
        report.sudo().write({'binding_model_id': False})
