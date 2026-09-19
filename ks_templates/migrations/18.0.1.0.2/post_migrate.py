# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Ensure Domestic Sales - Tax Invoice is bound to account.move and unhidden on module upgrade."""
    cr.execute("""
        UPDATE ir_act_report_xml
        SET binding_model_id = (SELECT id FROM ir_model WHERE model = 'account.move' LIMIT 1),
            binding_type = 'report',
            domain = NULL
        WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'ks_templates' AND name = 'action_report_domestic_tax_invoice'
        );

        DELETE FROM remove_action_report_action_data_rel_ah
        WHERE report_action_id IN (
            SELECT id FROM report_action_data
            WHERE ks_action_id IN (
                SELECT res_id FROM ir_model_data
                WHERE module = 'ks_templates' AND name = 'action_report_domestic_tax_invoice'
            )
        );
    """)
