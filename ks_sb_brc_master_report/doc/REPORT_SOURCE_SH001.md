# Report Source – SB/BRC Master (SH001)

**Structure:** Row 1 = Description (type or behaviour of the column). Row 2 = Actual name of the column.  
**Total: 62 columns.**

Where **Row 1** says "Text Box" or "Text box to enter amount" → field is an **input field** (editable, leave empty).

---

## Row 1 – Description (type / behaviour)

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 |
|---|--|--|--|--|--|--|--|--|----|----|----|----|----|----|----|----|----|----|----|----|
| System Generated | System Generated | Dropdown | Text Box | Text Box | Fetched from invoice | Fetched from invoice | Text Box | Fetched from invoice | Fetched from invoice | Fetched from invoice | Calendar | Fetched from invoice | Exchange rate during invoicing | Fetched from invoice | As per formula | From invoice | From invoice | From invoice | As per formula | Dropdown |
| **22** | **23** | **24** | **25** | **26** | **27** | **28** | **29** | **30** | **31** | **32** | **33** | **34** | **35** | **36** | **37** | **38** | **39** | **40** | **41** | **42** |
| Text box to enter amount | Text box to enter amount | Text box to enter amount | Text box to enter amount | Text box to enter amount | Text box to enter amount | Text box to enter amount | Text box to enter amount | Text box to enter amount | Text box to enter amount | Text box to enter amount | Text box to enter amount | Text box to enter amount | Text box to enter amount | Text box to enter amount | As per formula | Text box / from PL | Text box | Same as per formula | Same as per formula | Text Box |
| **43** | **44** | **45** | **46** | **47** | **48** | **49** | **50** | **51** | **52** | **53** | **54** | **55** | **56** | **57** | **58** | **59** | **60** | **61** | **62** |
| Dropdown | Dropdown | Dropdown | Calendar/date | Text Box | (BRC amount) | As per formula | Text Box | From Packing list | From Packing list | From goods outward | Calculated as per formula | Input | Dropdown (yes/no) | DBK only fresh units | 4% of FOB Value | Text Box | Text Box | Dropdown (Yes/No) | Text Box |

---

## Row 2 – Column name

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 |
|---|--|--|--|--|--|--|--|--|----|----|----|----|----|----|----|----|----|----|----|----|
| Sr. no. | Date | Invoice No | SB No | BE No | Consignee | Buyer | AWB NUMBER | QTY (KG) | Unit Rate | Currency | Calendar | Invoice Amount (USD) | EX Rate | SB Rate | Amount (INR) | FOB value (INR) | GST Rate | GST AMOUNT | Invoice Value | CHA |
| **22** | **23** | **24** | **25** | **26** | **27** | **28** | **29** | **30** | **31** | **32** | **33** | **34** | **35** | **36** | **37** | **38** | **39** | **40** | **41** | **42** |
| For calculation | Other Charges | Freight | Agency Charges | Bus Charges & FUMIGATION | Terminal handling | Drawback Charges | MIS Charges | Gate Pass | Transportation to Air Cargo | Load / Unload | Pallet Charges | Other Charges (2) | Local Warehouse | Insurance | Total | No. Of PALLATS | Weight as per AWB | For Planing Costing | Average For Costing | Airlines |
| **43** | **44** | **45** | **46** | **47** | **48** | **49** | **50** | **51** | **52** | **53** | **54** | **55** | **56** | **57** | **58** | **59** | **60** | **61** | **62** |
| Country | PORT | BRC Status | BRC DATE | BRC NO | BRC AMOUNT USD | Still in Realization | SB FOB value | Fresh | Activated | Other Country | RODTEP Amount | RODTEP AMOUNT PER SB | DBK % | DBK Claimed | DBK as Per Calculation | DBK Amount | Application Status | Drawback Received | Received Date |

---

## Mapping (62 columns)

| # | Row 1 (Behaviour) | Row 2 (Column name) |
|---|-------------------|---------------------|
| 1 | System Generated | Sr. no. |
| 2 | System Generated | Date |
| 3 | Dropdown | Invoice No |
| 4 | Text Box | SB No |
| 5 | Text Box | BE No |
| 6 | Fetched from invoice | Consignee |
| 7 | Fetched from invoice | Buyer |
| 8 | Text Box | AWB NUMBER |
| 9 | Fetched from invoice | QTY (KG) |
| 10 | Fetched from invoice | Unit Rate |
| 11 | Fetched from invoice | Currency |
| 12 | Calendar | Calendar |
| 13 | Fetched from invoice | Invoice Amount (USD) |
| 14 | Exchange rate during invoicing | EX Rate |
| 15 | Fetched from invoice | SB Rate |
| 16 | As per formula | Amount (INR) |
| 17 | From invoice | FOB value (INR) |
| 18 | From invoice | GST Rate |
| 19 | From invoice | GST AMOUNT |
| 20 | As per formula | Invoice Value |
| 21 | Dropdown | CHA |
| 22–36 | Text box to enter amount | For calculation … Insurance |
| 37 | As per formula | Total |
| 38 | Text box / from PL | No. Of PALLATS |
| 39 | Text box | Weight as per AWB |
| 40 | Same as per formula | For Planing Costing |
| 41 | Same as per formula | Average For Costing |
| 42 | Text Box | Airlines |
| 43 | Dropdown | Country |
| 44 | Dropdown | PORT |
| 45 | Dropdown | BRC Status |
| 46 | Calendar/date | BRC DATE |
| 47 | Text Box | BRC NO |
| 48 | (BRC amount) | BRC AMOUNT USD |
| 49 | As per formula | Still in Realization |
| 50 | Text Box | SB FOB value |
| 51 | From Packing list | Fresh |
| 52 | From Packing list | Activated |
| 53 | From goods outward | Other Country |
| 54 | Calculated as per formula | RODTEP Amount |
| 55 | Input | RODTEP AMOUNT PER SB |
| 56 | Dropdown (yes/no) | DBK % |
| 57 | DBK only fresh units | DBK Claimed |
| 58 | 4% of FOB Value | DBK as Per Calculation |
| 59 | Text Box | DBK Amount |
| 60 | Text Box | Application Status |
| 61 | Dropdown (Yes/No) | Drawback Received |
| 62 | Text Box | Received Date |

**Rule:** Row 1 = "Text Box" or "Text box to enter amount" → implement as **input field** (editable, no default).
