# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Hide the standard 'PDF' (account_invoices) and ensure Domestic Sales - Tax Invoice is bound and unhidden."""
    report = env.ref('account.account_invoices', raise_if_not_found=False)
    if report:
        report.sudo().write({'binding_model_id': False})

    env.cr.execute("""
        UPDATE ir_act_report_xml
        SET binding_model_id = (SELECT id FROM ir_model WHERE model = 'account.move' LIMIT 1),
            binding_type = 'report',
            domain = NULL
        WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'ks_templates' AND name LIKE 'action_report_domestic_tax%'
        );

        DELETE FROM remove_action_report_action_data_rel_ah
        WHERE report_action_id IN (
            SELECT id FROM report_action_data
            WHERE ks_action_id IN (
                SELECT res_id FROM ir_model_data
                WHERE module = 'ks_templates' AND name LIKE 'action_report_domestic_tax%'
            )
        );
    """)
