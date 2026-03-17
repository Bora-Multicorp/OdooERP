# ks_purchase_approval — Test Cases

Format per case:  
- **Description**  
- **Steps**  
- **Expected Outcome**  
- **Actual Outcome**

---

## TC1 – Normal user sends PO for confirmation (popup + pending_approval)
- **Steps**
  1. As a normal Purchase User (not a PM), create a PO in `draft`.
  2. Click `Confirm Order` (triggers the confirmation popup).
  3. Accept the popup.
- **Expected Outcome**
  - PO moves to `pending_approval`.
  - Chatter posts: “Confirmation request submitted by <user>. Waiting for approval from: <PM1>, <PM2>.”
  - PM1/PM2 subscribed; approval flags reset.
- **Actual Outcome**  
  _Fill after test run_

## TC2 – PM1 approves confirmation with reason (popup)
- **Steps**
  1. As PM1, open a PO in `pending_approval`.
  2. Click `Approve Confirmation`; enter a non-empty reason and submit.
- **Expected Outcome**
  - `ks_confirm_pm1_approved = True`; reason stored.
  - Chatter logs “<PM1> approved the PO. Reason: <reason>.”
  - State stays `pending_approval` until PM2 approves.
- **Actual Outcome**  
  _Fill after test run_

## TC3 – PM2 approves confirmation and finalizes PO
- **Steps**
  1. As PM2, open same PO (PM1 already approved).
  2. Click `Approve Confirmation`; enter reason and submit.
- **Expected Outcome**
  - `ks_confirm_pm2_approved = True`; reason stored.
  - Chatter logs PM2 reason.
  - Both approved ⇒ PO to `purchase` (or `done` if lock), final confirmation message posted; partner subscribed.
- **Actual Outcome**  
  _Fill after test run_

## TC4 – PM rejects confirmation (reason required)
- **Steps**
  1. As PM1 or PM2, open PO in `pending_approval`.
  2. Click `Reject Confirmation`; enter reason and submit.
- **Expected Outcome**
  - PO returns to `draft`; confirmation flags and request info cleared.
  - Chatter logs rejection with reason.
- **Actual Outcome**  
  _Fill after test run_

## TC5 – Normal user requests PO update (wizard + PM names)
- **Steps**
  1. Confirm a PO to `purchase`.
  2. As normal user, click `Request Update`; enter reason and submit.
- **Expected Outcome**
  - PO goes `update_requested`; request info and flags reset.
  - Chatter: “Update request submitted by <user>. Waiting for approval from: <PM1>, <PM2>. Reason: <reason>.”
  - PM1/PM2 for updates subscribed.
- **Actual Outcome**  
  _Fill after test run_

## TC6 – PM approves update with reason popup (PM1)
- **Steps**
  1. As PM1, open PO in `update_requested`.
  2. Click `Approve Update`; enter reason and submit.
- **Expected Outcome**
  - `ks_update_pm1_approved = True`; reason logged in chatter.
  - State remains `update_requested` until PM2 approves.
- **Actual Outcome**  
  _Fill after test run_

## TC7 – PM approves update with reason popup (PM2 completes)
- **Steps**
  1. As PM2, open same PO (PM1 approved).
  2. Click `Approve Update`; enter reason and submit.
- **Expected Outcome**
  - `ks_update_pm2_approved = True`; reason logged.
  - Both approved ⇒ PO back to `purchase`, `ks_update_approved = True`; chatter notes requester can edit.
- **Actual Outcome**  
  _Fill after test run_

## TC8 – PM rejects update (reason required)
- **Steps**
  1. As PM1 or PM2, open PO in `update_requested`.
  2. Click `Reject Update`; enter reason and submit.
- **Expected Outcome**
  - PO returns to `purchase`; update flags and request info cleared.
  - Chatter logs rejection with reason.
- **Actual Outcome**  
  _Fill after test run_

## TC9 – Normal user requests PO cancel (wizard)
- **Steps**
  1. PO in `purchase`.
  2. As normal user, click `Request Cancel`; enter reason and submit.
- **Expected Outcome**
  - PO moves to `cancel_requested`; request info set; flags reset.
  - Chatter logs cancellation request with reason; PM1/PM2 for cancel subscribed.
- **Actual Outcome**  
  _Fill after test run_

## TC10 – PM approves cancel (both PMs)
- **Steps**
  1. As PM1, approve cancel; as PM2, approve cancel.
- **Expected Outcome**
  - After both, PO state `cancel`; final cancel approval message posted.
- **Actual Outcome**  
  _Fill after test run_

## TC11 – PM rejects cancel (reason required)
- **Steps**
  1. As PM1 or PM2, click `Reject Cancel`; enter reason.
- **Expected Outcome**
  - PO returns to `purchase`; cancel flags cleared; chatter logs reason.
- **Actual Outcome**  
  _Fill after test run_

## TC12 – Button visibility by role/state
- **Steps**
  1. Check form as normal user vs PM across states (`draft`, `pending_approval`, `update_requested`, `cancel_requested`, `purchase`, `done`).
- **Expected Outcome**
  - Buttons follow computed visibility fields (`ks_show_*`) per design: normal user sees request buttons; PM sees approve/reject where applicable; unlock only for PM in `done`.
- **Actual Outcome**  
  _Fill after test run_

## TC13 – Approval config validations
- **Steps**
  1. Try saving config with same PM1/PM2 for confirm/update/cancel.
- **Expected Outcome**
  - ValidationError requiring distinct PM1 and PM2.
- **Actual Outcome**  
  _Fill after test run_

## TC14 – Unauthorized approvals blocked
- **Steps**
  1. As a normal user, attempt any approve/reject action.
- **Expected Outcome**
  - UserError “not authorized” raised; no state change; no chatter entry.
- **Actual Outcome**  
  _Fill after test run_

## TC15 – Update edit completion flow
- **Steps**
  1. After both PMs approve update, as requester edit PO, then click `Complete Update`.
- **Expected Outcome**
  - Update flags cleared; chatter “Update completed…”; PO locked again for requester.
- **Actual Outcome**  
  _Fill after test run_

---

## Negative / Edge Cases

### TC16 – Confirm without approval config
- **Steps**
  1. Remove/disable approval config for the company.
  2. As normal user, create PO in `draft` and click `Confirm Order`.
- **Expected Outcome**
  - Falls back to standard Odoo confirm or raises configured error (per module behavior).
  - No pending_approval state; no PM chatter entry.
- **Actual Outcome**  
  _Fill after test run_

### TC17 – Confirm request when already pending
- **Steps**
  1. Put PO in `pending_approval`.
  2. Try to confirm again as normal user.
- **Expected Outcome**
  - UserError: only Draft/Sent can be confirmed; state unchanged; no new chatter.
- **Actual Outcome**  
  _Fill after test run_

### TC18 – Approve confirmation twice by same PM
- **Steps**
  1. PO in `pending_approval`, PM1 approves once with reason.
  2. PM1 clicks Approve again.
- **Expected Outcome**
  - UserError “already approved”; no duplicate chatter; flags unchanged.
- **Actual Outcome**  
  _Fill after test run_

### TC19 – Unauthorized approval attempt
- **Steps**
  1. As a user who is not PM1/PM2, try Approve Confirmation or Approve Update.
- **Expected Outcome**
  - UserError “not authorized”; no state change; no chatter.
- **Actual Outcome**  
  _Fill after test run_

### TC20 – Empty reason on approval popup
- **Steps**
  1. Open approval popup (confirmation or update) as PM.
  2. Submit with empty/whitespace reason.
- **Expected Outcome**
  - Validation error; wizard stays open; no chatter/state change.
- **Actual Outcome**  
  _Fill after test run_

### TC21 – Reject without reason
- **Steps**
  1. Open reject wizard (confirm/update/cancel) as PM.
  2. Submit with empty reason.
- **Expected Outcome**
  - Validation error; no state change; no chatter.
- **Actual Outcome**  
  _Fill after test run_

### TC22 – Update request when already approved for edit
- **Steps**
  1. PO in `purchase` with `ks_update_approved = True`.
  2. Normal user tries `Request Update` again.
- **Expected Outcome**
  - UserError “update already approved”; no new state/chatter.
- **Actual Outcome**  
  _Fill after test run_

### TC23 – Approve update twice by same PM
- **Steps**
  1. PO in `update_requested`, PM1 approves with reason.
  2. PM1 clicks Approve Update again.
- **Expected Outcome**
  - UserError “already approved”; no duplicate chatter; flags unchanged.
- **Actual Outcome**  
  _Fill after test run_

### TC24 – Cancel request in invalid state
- **Steps**
  1. PO in `draft` or `pending_approval`.
  2. Normal user clicks `Request Cancel`.
- **Expected Outcome**
  - UserError per rules (only confirmed POs can request cancel); no state change; no chatter.
- **Actual Outcome**  
  _Fill after test run_


