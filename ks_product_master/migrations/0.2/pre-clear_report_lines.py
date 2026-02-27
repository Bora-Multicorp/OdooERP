# -*- coding: utf-8 -*-
"""Clear report line tables before FK is changed to reference new header tables.

Runs on upgrade so that margin_analysis_report and ad_margin_report no longer
contain rows with report_id pointing to old transient wizard tables.
"""


def migrate(cr, version):
    for table in ('margin_analysis_report', 'ad_margin_report'):
        cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = current_schema() AND table_name = %s
            )
        """, (table,))
        if cr.fetchone()[0]:
            cr.execute("DELETE FROM " + table)
