from . import models
from . import wizard


def post_init_hook(env):
    env.cr.execute("""
        UPDATE mail_activity ma
        SET res_name = CASE
            WHEN rp.name IS NOT NULL AND rp.name != '' THEN po.name || ' - ' || rp.name
            ELSE po.name
        END
        FROM purchase_order po
        LEFT JOIN res_partner rp ON po.partner_id = rp.id
        WHERE (ma.res_model = 'purchase.order' OR ma.res_model_id = (SELECT id FROM ir_model WHERE model = 'purchase.order'))
          AND ma.res_id = po.id;
    """)

