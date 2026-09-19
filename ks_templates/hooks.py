# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Hide the standard 'PDF' (account_invoices) and ensure Domestic Sales - Tax Invoice is bound and unhidden."""
    report = env.ref('account.account_invoices', raise_if_not_found=False)
    if report:
        report.sudo().write({'binding_model_id': False})

    dom_report = env.ref('ks_templates.action_report_domestic_tax_invoice', raise_if_not_found=False)
    move_model = env.ref('account.model_account_move', raise_if_not_found=False)
    if dom_report and move_model:
        dom_report.sudo().write({
            'binding_model_id': move_model.id,
            'binding_type': 'report',
            'domain': False,
        })

    env.cr.execute("""
        DELETE FROM remove_action_report_action_data_rel_ah
        WHERE report_action_id IN (
            SELECT id FROM report_action_data
            WHERE ks_action_id IN (
                SELECT res_id FROM ir_model_data
                WHERE module = 'ks_templates' AND name = 'action_report_domestic_tax_invoice'
            )
        );
    """)
