# KS Insurance Management

<p align="center">
  <strong>Comprehensive Insurance Policy Management for Odoo 18</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Odoo-18.0-875A7B?style=for-the-badge&logo=odoo" alt="Odoo 18"/>
  <img src="https://img.shields.io/badge/License-LGPL--3-green?style=for-the-badge" alt="License"/>
  <img src="https://img.shields.io/badge/Module-Application-blue?style=for-the-badge" alt="Application"/>
</p>

---

## 📋 Overview

**KS Insurance Management** helps you manage insurance policies, declarations, and reports in one place. Create **individual** or **floater** policies, record **Marine** and **Fire & Burglary** declarations, generate PDF reports, and link policies to **Accounting payments**—with multi-company and multi-currency support.

| Feature | Description |
|--------|-------------|
| **Policies** | Individual & floater policies with types (Marine, Fire & Burglary, Miscellaneous) |
| **Declarations** | Marine (sales value) & Fire & Burglary (inventory value) with email & PDF |
| **Reports** | Fire & Burglary, Marine, and Miscellaneous insurance reports |
| **Payments** | Create a policy directly from an Accounting payment (premium → policy) |
| **Automation** | Auto-expire policies and 30-day expiry reminders |

---

## 🚀 Quick Start

### Prerequisites

- **Odoo 18** with modules: **Accounting**, **Inventory**, **Mail**, **Base**
- User access: **Insurance User** or **Insurance Administrator**

### Installation

1. Install the module **KS Insurance Management** from Apps.
2. Assign users to **Insurance User** or **Insurance Administrator** (Settings → Users & Companies → Users).
3. (Optional) Configure **Insurance → Configuration** (Administrator only): Categories, Types, Companies, Agents.

---

## 📋 Requirements Compliance (Insurance Module Details)

The module aligns with the functional requirements document and report formats under `static/Files/`:

| Requirement | Implementation |
|-------------|----------------|
| **Insurance Type** – Admin only CRUD; dropdown on forms | Configuration → Insurance Types (group_insurance_admin); types on policy/declaration |
| **Policy number** – Manual entry; creation from payment | `policy_number` (Char); popup from Payment Entry creates policy with all fields |
| **Cover amount in words** | `sum_insured_words` on policy (auto from Sum Insured) |
| **Premium from invoice/payment** | Payment popup & policy: Premium (Incl. GST); Total Premium Paid from linked payments |
| **Individual / Floater** | Policy Type; Floater = multiple Covered Locations (warehouses) |
| **Categories** – Fire, Burglary, Marine, GMC, GPA, Vehicle, Personal, Office, HO Assets | Data + Configuration → Insurance Categories; admin only |
| **Miscellaneous report** | Policies with category `is_misc`; report in menu |
| **Marine declarations** – Sales value (incl. GST), configurable, email draft | Declaration Type Marine; sales from posted invoices; email template + PDF |
| **Marine declaration format (xlsx)** | Declaration Letter PDF: invoice-wise table (Sr. no, Invoice No., Invoice date, Invoice value), Total, Balance Sum Insured |
| **Fire & Burglary declarations** – Inventory per warehouse | Declaration Type Fire & Burglary; warehouse; average inventory value |
| **F&B Report** | Fire & Burglary Report (Policy No., Type, Company, Insurer, Sum Insured, Premium, Avg Inventory, Expiry, Status) |
| **Marine Report** – Applicability, Balance Sum Insured | Marine Insurance Report; EXIM/Domestic/Both/Russia; balance column; last two columns reference only |
| **Sum insured reset on expiry** | Mark as Expired sets Marine balance to 0; status = Expired |
| **Declaration Download** – Date From/To, companies, bulk | Bulk Declaration Download wizard; companies multi-select; Generate & Download |

Reference files in `static/Files/`: **Insurance Module Details (1).docx** (requirements), **Marine_Declaration_*.xlsx** / **SSK INCORPORATION_MARINE DECLARATION (1).xlsx** (report layout reference).

---

## 📚 Key Concepts

| Term | Meaning |
|------|--------|
| **Policy** | One insurance contract: type, insurer, sum insured, premium, dates, status (Active/Expired). |
| **Individual** | Policy covering a single risk/location. |
| **Floater** | Policy covering multiple warehouses; at least one **Covered Location** must be selected. |
| **Declaration** | Statement sent to insurer: **Marine** = sales value for a period; **Fire & Burglary** = average inventory value for a warehouse. |
| **Balance Sum Insured** | (Marine) Remaining cover after declarations deduct from sum insured. |
| **Insurance Type** | e.g. Marine, Fire & Burglary; linked to a **Category** (Fire, Marine, GMC, etc.). |

---

## 📁 Menu Structure

```
Insurance
├── Insurance Master
│   └── All Policies
├── Declarations
│   ├── All Declarations
│   └── Bulk Declaration Download
├── Reports
│   ├── Fire & Burglary Report
│   ├── Marine Insurance Report
│   └── Miscellaneous Insurance Report
└── Configuration (Administrator only)
    ├── Insurance Types
    ├── Insurance Categories
    ├── Insurance Companies
    └── Agents
```

---

## 🔧 Process 1 — Configuration (Master Data)

**Who:** Insurance Administrator

### Insurance Categories

- **Insurance → Configuration → Insurance Categories**
- Preloaded: Fire, Burglary, Marine, GMC, GPA, Vehicle, Personal, Office Space, HO Assets.
- Check **Miscellaneous** so policies appear in the **Miscellaneous Insurance Report**.

### Insurance Types

- **Insurance → Configuration → Insurance Types**
- Link each type to a **Category**.
- Set **Is Marine Insurance** and/or **Is Fire & Burglary** so policies appear in the right reports and declaration types.
- **Marine Applicability:** EXIM / Domestic / Both / Russia Only.

### Insurance Companies & Agents

- **Insurance Companies:** Name, contact person, phone, email, address.
- **Agents:** Name, phone, email, license number; optionally link to an Insurance Company.

---

## 📄 Process 2 — Insurance Policies

**Who:** Insurance User or Administrator

### Create a Policy Manually

1. **Insurance → Insurance Master → All Policies** → **Create**
2. Fill in:
   - **Policy Number**, **Insurance Type** (required), **Insurance Company** (required), **Agent** (optional)
   - **Policy Type:** Individual or **Floater** (if Floater, select at least one **Covered Location**)
   - **Currency**, **Sum Insured**, **Premium (Incl. GST)**, **Expiry Date** (required)
3. Save → Reference and **Sum Insured (in Words)** are auto-generated.

**Rules:**

- Floater policies must have **at least one covered location**.
- **Expiry Date** must be on or after **Start Date** (if both are set).

### Policy Status & Expiry

- **Status:** Active / Expired.
- **Mark as Expired:** Open policy → use the **Mark as Expired** button (for Marine, Balance Sum Insured is set to 0).
- **Scheduled jobs:**
  - **Auto-Expire Policies:** Marks active policies with expiry date &lt; today as Expired.
  - **Expiry Reminder (30 days):** Posts a chatter message on policies expiring within 30 days.

---

## 💳 Process 3 — Create Policy from Payment

**Who:** User with Accounting + Insurance access

1. **Accounting → Payments** → Create a payment (e.g. Outbound) in **Draft**.
2. Open the payment → **Insurance Details** tab → **Add Insurance Details**.
3. In the popup: Company, Insurance Type, Policy Number, Sum Insured, Expiry Date, Policy Type, Agent, Insurance Company; for Floater add **Covered Locations**. **Premium** is filled from the payment amount.
4. Click **Confirm & Create Policy** → Policy is created and linked to the payment; you are redirected to the new policy.

---

## 📝 Process 4 — Declarations

**Who:** Insurance User or Administrator

### Create a Declaration

1. **Insurance → Declarations → All Declarations** → **Create**
2. **Policy**, **Declaration Type** (Marine / Fire & Burglary), **Date From**, **Date To**, **Company**
3. **Marine:** Sales Amount and Declaration Amount are computed from **posted customer invoices** in the period (editable). Set **Marine Applicability** if needed.
4. **Fire & Burglary:** Select **Warehouse**; Average Inventory Value and Declaration Amount are computed from **stock valuation** for that warehouse.
5. Save (status = **Draft**). **Date To** must be ≥ **Date From**.

### Confirm, Email, Print

- **Confirm:** Status → Confirmed. For **Marine**, the policy’s **Balance Sum Insured** is reduced by the declaration amount.
- **Draft Email:** Opens composer with the declaration email template (optional PDF attachment).
- **Print:** Generates the **Declaration Letter** PDF.

---

## 📦 Process 5 — Bulk Declaration Download

**Who:** Insurance User or Administrator

1. **Insurance → Declarations → Bulk Declaration Download**
2. **Date From**, **Date To**, **Declaration Type** (Marine / Fire & Burglary / Both), **Companies**
3. **Generate & Download** → Creates draft declarations for all matching active policies (or reuses existing ones) and opens one **Declaration Letter** PDF.

---

## 📊 Process 6 — Reports

**Who:** Insurance User or Administrator

| Report | Menu | Content |
|--------|------|--------|
| **Fire & Burglary** | Reports → Fire & Burglary Report | Active Fire & Burglary policies; sum insured, premium, avg inventory, expiry |
| **Marine** | Reports → Marine Insurance Report | Active Marine policies; balance sum insured, declaration count |
| **Miscellaneous** | Reports → Miscellaneous Insurance Report | Active policies in Miscellaneous categories (GMC, GPA, etc.) |

For each report: set **Date From**, **Date To**, **Companies** → click the corresponding **Print** button to get the PDF.

---

## 🔐 Access Rights

| Role | Policies | Declarations | Categories/Types | Companies/Agents | Configuration |
|------|----------|--------------|------------------|------------------|---------------|
| **Insurance User** | Create, edit (no delete) | Create, edit | Read only | Create, edit (no delete) | No access |
| **Insurance Administrator** | Full access | Full access | Full access | Full access | Full access |

- **Configuration** menu is visible only to **Insurance Administrator**.
- **Multi-company:** Users see data for their allowed companies (or shared records).
- **Multi-currency:** Each policy has a **Currency** field (default = company currency).

---

## 💡 Tips & Best Practices

- Use **Insurance Type** and **Category** consistently so reports and bulk declaration work correctly.
- For **Floater** policies, always select at least one warehouse.
- **Confirm** declarations only when amounts are final (Marine confirmation reduces Balance Sum Insured).
- Use **Bulk Declaration Download** for period-end batches.
- Rely on **Expiry Reminder** and **Mark as Expired** (or the cron) to keep policies up to date.

---

## ❓ FAQ

**Q: Can I edit a declaration after Confirm?**  
Yes. For Marine, Balance Sum Insured is already reduced; adjust the policy manually if you need to correct the balance.

**Q: Why is Declaration Amount 0 for Marine?**  
It is computed from **posted** customer invoices in the selected date range and company. Check period, company, and that invoices are posted.

**Q: Why is Average Inventory Value 0 for Fire & Burglary?**  
It comes from stock (quants) in the chosen warehouse. Ensure the warehouse is set and products have cost/valuation.

**Q: Who can change Categories and Types?**  
Only **Insurance Administrator** (Configuration menu).

**Q: How do I get expiry reminders?**  
The scheduled action **Insurance: Expiry Reminder (30 days)** runs daily and posts a message on policies expiring within 30 days. Ensure crons are active.

---

## 📎 Related Odoo Apps

- **Accounting** — Payments and invoices (premium payments; Marine declaration amounts).
- **Inventory** — Warehouses for Floater locations and Fire & Burglary inventory value.
- **Mail** — Chatter and declaration email template.

---

<p align="center">
  <sub><strong>KS Insurance Management</strong> · Odoo 18 · Ksolves</sub>
</p>
