import json

from odoo.tools.safe_eval import safe_eval


def replace_company_domain(domain, company_id, company_ids):
    domain = safe_eval(domain) if isinstance(domain, str) else domain
    new_domain = []
    for condition in domain:
        if isinstance(condition, tuple) and len(condition) >= 3:
            if condition[1] in ('in', 'not in') and isinstance(condition[2], list) and '%MYCOMPANY' in condition[2]:
                new_condition = (condition[0], condition[1], [y for x in condition[2] for y in (company_ids if x == '%MYCOMPANY' else [x])])
            elif condition[2] == '%MYCOMPANY':
                new_condition = (condition[0], condition[1], company_id)
            else:
                new_condition = condition
            new_domain.append(new_condition)
        else:
            new_domain.append(condition)
    return json.dumps(new_domain)

def clean_dict_in_place(data):
    """Removes non-serializable keys from a dictionary in place."""
    for key in list(data.keys()):
        try:
            json.dumps(data[key])
        except (TypeError, OverflowError):
            del data[key]