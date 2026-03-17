# Analytic Account Multi-Company Module

## Overview

This module makes Odoo's analytic accounts fully company-independent, allowing them to be shared across all companies in a multi-company environment. This is particularly useful for organizations that want to track analytics consistently across different legal entities.

## Features

- **Company-Independent Analytic Accounts**: Analytic accounts can be created without a company assignment, making them accessible to all companies
- **Cross-Company Usage**: Analytic accounts can be used in accounting entries, expenses, projects, timesheets, sales orders, purchases, and stock moves across all companies
- **No Multi-Company Access Errors**: All security rules and record rules are configured to allow company-independent accounts
- **Currency Handling**: Currency is computed dynamically based on the current company when viewing company-independent accounts

## Technical Details

### Changes Made

1. **Model Override (`account.analytic.account`)**:
   - Disabled `_check_company_auto` to allow company-independent accounts
   - Removed default `company_id` value (allows `False`/`None`)
   - Made `currency_id` computed instead of related to handle company-independent accounts
   - Updated `_check_company_consistency` constraint to allow company-independent accounts

2. **View Updates**:
   - Enhanced form view to indicate company field is optional
   - Updated list view to show company column appropriately

3. **Security Rules**:
   - Existing security rules already support company-independent accounts:
     - `analytic_comp_rule`: `['|',('company_id','=',False),('company_id', 'parent_of', company_ids)]`
   - No changes needed to security rules

### How It Works

- **Creating Company-Independent Accounts**: Simply leave the `company_id` field empty when creating an analytic account
- **Using Across Companies**: Company-independent analytic accounts appear in all company contexts and can be selected in any transaction
- **Currency Display**: For company-independent accounts, the currency shown is the current company's currency (computed dynamically)

## Usage

### Creating a Company-Independent Analytic Account

1. Navigate to **Accounting > Analytics > Analytic Accounts**
2. Click **Create**
3. Fill in the required fields (Name, Plan)
4. **Leave the Company field empty** (or set it to `False`)
5. Save

### Using in Transactions

Company-independent analytic accounts will appear in:
- Accounting entries (Journal Items)
- Expense entries
- Project/Task linkage
- Timesheets
- Sales orders and invoices
- Purchase orders and vendor bills
- Stock moves and landed costs
- Any other module referencing analytic accounts

## Compatibility

- **Odoo Version**: 18.0
- **Dependencies**: `analytic`, `account`
- **Compatible with**: All standard Odoo modules that use analytic accounts

## Notes

- Company-independent accounts are visible to all companies
- The security rule already supports this: `['|',('company_id','=',False),('company_id', 'parent_of', company_ids)]`
- Currency is computed based on the current company context for company-independent accounts
- All existing company-specific analytic accounts continue to work as before

## Installation

1. Place this module in your custom addons directory
2. Update the apps list in Odoo
3. Install the "Analytic Account Multi-Company" module
4. Restart Odoo if needed

## Author

Ksolves

## License

LGPL-3


