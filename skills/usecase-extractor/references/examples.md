# Use Case Extraction Examples

This reference provides detailed examples of use case extraction patterns across different document types and domains. Each example prints only part of its full analysis: dependency codes such as `USR-001` or `CST-003` belong to use cases that exist in the complete extraction but are not shown here.

## Example 1: E-Commerce Platform Requirements

### Source Requirement
"The system shall allow registered users to add products to their shopping cart, view cart contents, update quantities, and proceed to checkout. Users must be authenticated to access cart functionality."

### Extracted Use Cases

**Role: Customer (CST)**

A registered shopper who browses the catalog and buys from it. The customer owns their
own cart and orders, and holds no administrative rights over the platform.

#### Use Case CST-001: Add Product to Cart

**Code**: CST-001

**Name**: Add Product to Cart

**Title**: CST-001: Add Product to Cart

**Priority**: High

**Target**: Enable customers to select a product and add it to their shopping cart. The cart holds the selection for a later purchase, so the customer does not have to decide immediately. The shopping session is kept across page navigations, which lets the customer keep browsing without losing the cart. This supports incremental cart building: the customer collects several items before a single checkout.

**Main Flow**:
1. Customer opens a product page and selects quantity and variant
2. System validates product availability
3. System adds the item to the cart and updates totals
4. System confirms the addition and shows the updated cart summary

**Variations**:
- **2a. Product unavailable**: system blocks the addition and suggests similar available products
- **2b. Quantity exceeds stock**: system caps the quantity to available stock and informs the customer

**Input Data**:

*Mandatory*:
- User authentication token
- Product ID
- Quantity (default: 1)
- Product availability status

*Optional*:
- Product variant (size, color)
- Gift wrapping preference
- Special instructions

**Output Data**:
- Updated cart item count
- Updated cart total amount
- Confirmation message
- Updated cart session
- Product availability notification (if low stock)
- Cart persistence record

**Dependencies**:
- USR-001: User Authentication (prerequisite)
- CST-003: View Product Details (data dependency)

**Source**: «The system shall allow registered users to add products to their shopping cart…»

**User Story**: As a customer, I want to add products to my cart, so that I can collect items and buy them in one order later.

**Acceptance Criteria**:
1. Given an authenticated customer on an available product page, when they add a quantity up to the available stock, then the cart updates and shows the new totals
2. Given an unavailable product, when the customer tries to add it, then the addition is blocked and similar products are suggested

#### Use Case CST-002: View Shopping Cart

**Code**: CST-002

**Name**: View Shopping Cart

**Title**: CST-002: View Shopping Cart

**Priority**: Medium

**Target**: Allow customers to review all items currently in their shopping cart, together with pricing details and each item's availability. The review lets the customer decide whether to proceed to checkout or keep shopping.

**Main Flow**:
1. Customer opens the cart page
2. System loads the active cart session and lists all items with prices
3. System shows subtotal, tax, shipping estimate, and grand total

**Variations**:
- **3a. Promotional code applied**: system recalculates the totals and shows the savings

**Input Data**:

*Mandatory*:
- User authentication token
- Active cart session ID

*Optional*:
- Promotional code (for preview)
- Shipping postal code (for estimate)

**Output Data**:
- List of cart items with details
- Item-level pricing
- Subtotal
- Tax estimate
- Shipping estimate
- Grand total
- Availability status for each item
- Promotional savings (if applicable)

**Dependencies**:
- CST-001: Add Product to Cart (data dependency)
- USR-001: User Authentication (prerequisite)

**Source**: «…view cart contents, update quantities, and proceed to checkout»

**User Story**: As a customer, I want to review my cart with all costs, so that I can decide whether to check out or keep shopping.

---

## Example 2: Healthcare Management System

### Source Requirement
"Medical staff must be able to access patient records, view medical history, update diagnoses, prescribe medications, and schedule follow-up appointments. All actions must be logged for HIPAA compliance."

### Extracted Use Cases

**Role: Medical Staff (MED)**

Clinicians and nurses who treat patients. Medical staff read and update clinical records within the limits of their assigned permissions, and every action they take is auditable.

#### Use Case MED-001: Access Patient Record

**Code**: MED-001

**Name**: Access Patient Record

**Title**: MED-001: Access Patient Record

**Priority**: High

**Target**: Enable medical staff to retrieve the complete information held about a patient. The record covers demographics, medical history, current medications, known allergies, and recent visits. Access is secured, so only staff with the right permissions and a stated reason can open the record. The retrieved information supports clinical decision-making and continuity of care between visits.

**Main Flow**:
1. Staff member authenticates and searches for the patient by identifier
2. System verifies role permissions and access justification
3. System retrieves the complete patient record
4. System logs the access for compliance with the Health Insurance Portability and Accountability Act (HIPAA) and displays the record

**Variations**:
- **2a. Insufficient permissions**: system denies access, logs the attempt, and notifies the supervisor
- **3a. Patient not found**: system reports no match and offers a refined search

**Input Data**:

*Mandatory*:
- Staff authentication credentials
- Staff role and permissions
- Patient identifier: medical record number (MRN) or social security number (SSN)
- Access reason/justification
- Access timestamp

*Optional*:
- Specific record section filter
- Date range filter
- Related family member records flag

**Output Data**:
- Patient demographic information
- Medical history summary
- Active medications list
- Known allergies and adverse reactions
- Recent visit summaries
- Current diagnoses
- Insurance information
- Emergency contact details
- HIPAA-compliant access log entry
- Staff notification of sensitive information flags

**Dependencies**:
- USR-001: User Authentication (prerequisite)
- SYS-001: HIPAA Compliance Logging (triggering)

**Source**: «Medical staff must be able to access patient records, view medical history…»

**User Story**: As a medical staff member, I want to retrieve the full patient record, so that I can make safe clinical decisions.

**Acceptance Criteria**:
1. Given staff with valid credentials and an access justification, when they request a patient record, then the full record is displayed and the access is logged
2. Given staff without sufficient permissions, when they request a record, then access is denied, the attempt is logged, and the supervisor is notified

**Role: System (SYS)**

Automated hospital-system processes with no human operator. They run inside a use case started by someone else and record what happened, rather than take clinical decisions.

#### Use Case SYS-001: HIPAA Compliance Logging

**Code**: SYS-001

**Name**: HIPAA Compliance Logging

**Title**: SYS-001: HIPAA Compliance Logging

**Priority**: Medium

**Target**: Automatically capture all access and modifications to patient records. The resulting audit trail serves regulatory compliance, security monitoring, and breach investigation.

**Main Flow**:
1. A patient-data use case starts (view, edit, create, or delete)
2. System captures user, action, patient, timestamp, and location
3. System writes an immutable audit log entry and indexes it for reports

**Variations**:
- **3a. Suspicious access pattern**: system raises a security alert in addition to the log entry

**Input Data**:

*Mandatory*:
- User ID and role
- Action type (view, edit, create, delete)
- Patient ID
- Timestamp
- Access location (IP address, workstation)
- Data fields accessed or modified

*Optional*:
- Session ID
- Access justification

**Output Data**:
- Immutable audit log entry
- Compliance report data point
- Security monitoring alert (if suspicious pattern)
- Timestamp verification record
- Digital signature of log entry
- Backup compliance record

**Dependencies**:
- None — triggered automatically by every use case that touches patient data (e.g., MED-001)

**Source**: «All actions must be logged for HIPAA compliance» (inferred)

**User Story**: As an auditor, I want every access to patient data logged automatically, so that HIPAA compliance can be verified at any time.

**Role: Auditor (AUD)**

A compliance function that reviews how patient data was accessed and changed. The auditor reads the audit trail and never edits clinical content.

#### Use Case AUD-001: Generate Annual Compliance Report

**Code**: AUD-001

**Name**: Generate Annual Compliance Report

**Title**: AUD-001: Generate Annual Compliance Report

**Priority**: Low

**Target**: Produce the year's summary of every access to patient records for the compliance office's annual HIPAA review.

**Main Flow**:
1. Auditor requests the annual report and picks the year
2. System aggregates the year's audit log entries and renders the report
3. System stores the report file in the audit archive and confirms to the auditor

**Variations**:
- **2a. No log entries for the year**: system reports the empty year and creates no file

**Input Data**:

*Mandatory*:
- Auditor authentication credentials
- Report year

*Optional*:
- Department filter

**Output Data**:
- Annual compliance report file
- Archive storage confirmation

**Dependencies**:
- SYS-001: HIPAA Compliance Logging (data dependency)

**Source**: «All actions must be logged for HIPAA compliance» (inferred)

**User Story**: As an auditor, I want the year's access history summarized once a year, so that the annual review has its evidence ready.

---

## Example 3: Financial Trading Platform

### Source Requirement
"The platform must support real-time trade execution with pre-trade risk checks, post-trade confirmation, and automated regulatory reporting."

### Extracted Use Cases

**Role: Trader (TRD)**

A licensed dealer who submits buy and sell orders for the firm's accounts. The trader works inside risk limits set by compliance and owns the resulting positions.

#### Use Case TRD-001: Execute Trade Order

**Code**: TRD-001

**Name**: Execute Trade Order

**Title**: TRD-001: Execute Trade Order

**Priority**: High

**Target**: Enable traders to submit buy or sell orders for financial instruments and have them executed in real time. Every order is checked against the firm's risk limits before it reaches the market. The trade is also reported to meet regulatory requirements. The trader receives an immediate confirmation together with the updated position and cash balance.

**Main Flow**:
1. Trader submits order details (instrument, type, quantity, side, account)
2. System runs the pre-trade risk check
3. System executes the order on the market
4. System books commission and updates position and cash balance
5. System sends confirmation and reports the trade to the regulator

**Variations**:
- **2a. Risk check fails**: system rejects the order, explains the breach, and suggests alternatives
- **3a. Partial fill**: system reports filled and remaining quantity and keeps the order working

**Input Data**:

*Mandatory*:
- Trader authentication and authorization
- Security identifier: international securities identification number (ISIN) or ticker
- Order type (market, limit, stop)
- Quantity
- Side (buy/sell)
- Account/portfolio ID
- Current market price

*Optional*:
- Limit price (for limit orders)
- Stop price (for stop orders)
- Time in force: day, good-til-cancelled (GTC), immediate-or-cancel (IOC)
- Execution instructions (all-or-none)
- Algorithmic trading strategy

**Output Data**:
- Order confirmation ID
- Execution price(s)
- Filled quantity
- Remaining quantity (if partial fill)
- Commission charged
- Updated portfolio position
- Updated cash balance
- Trade confirmation document
- Regulatory reporting record
- Market data update trigger
- Risk metrics recalculation trigger
- Confirmation notification: email or short message service (SMS)

**Dependencies**:
- SYS-001: Pre-Trade Risk Check (prerequisite)
- SYS-002: Market Data Feed (data dependency)
- USR-001: User Authentication (prerequisite)
- REG-001: Regulatory Trade Reporting (triggering)

**Source**: «The platform must support real-time trade execution…»

**User Story**: As a trader, I want to submit orders with an automatic risk check, so that I stay within limits while executing immediately.

**Acceptance Criteria**:
1. Given a trader within all risk limits, when an order is submitted, then it executes and a confirmation with updated positions is returned
2. Given an order that fails the pre-trade risk check, when it is submitted, then it is rejected with the breach explained and alternatives suggested

**Role: System (SYS)**

Automated platform processes with no human operator. They run inside a use case started by someone else, and they enforce rules rather than take business decisions.

#### Use Case SYS-001: Pre-Trade Risk Check

**Code**: SYS-001

**Name**: Pre-Trade Risk Check

**Title**: SYS-001: Pre-Trade Risk Check

**Priority**: Medium

**Target**: Automatically validate proposed trades against risk limits, margin requirements, and regulatory constraints before execution. The check prevents violations and protects firm capital.

**Main Flow**:
1. A trade order arrives for validation
2. System loads positions, margin, risk limits, and market volatility
3. System computes risk utilization and margin requirement
4. System returns pass or fail with reasons

**Variations**:
- **4a. Limit breach**: system fails the check, records the breach warning, and suggests a reduced quantity

**Input Data**:

*Mandatory*:
- Proposed trade details
- Current portfolio positions
- Account balance and margin
- Risk limit parameters
- Market volatility data
- Regulatory constraints

*Optional*:
- Historical trade patterns
- Stress test scenarios

**Output Data**:
- Risk check result (pass/fail)
- Risk utilization percentage
- Margin requirement calculation
- Limit breach warnings
- Risk metrics update
- Approval/rejection notification
- Audit log entry
- Alternative trade suggestions (if rejected)

**Dependencies**:
- TRD-001: Execute Trade Order (workflow sequence)

**Source**: «…with pre-trade risk checks…» (inferred)

**User Story**: As a compliance officer, I want every trade validated against risk limits before execution, so that no breach reaches the market.

---

## Example 4: Plant Maintenance — Italian Source, English Output

The first three examples read an English source and write English. This one reads Italian and
writes English, which is where the Languages rules of `SKILL.md` bite. Four of them are visible
below:

- The prefixes come from the **Italian** role names (`Tecnico` → `TEC`, `Capoarea` → `CAP`) and
  stay the same whatever the output language; the legend gives each one its role name in English.
  `SYS` is a standard prefix, so it is already the same word in both languages.
- Each `Source` quotes the **Italian** wording, untranslated.
- The document's own vocabulary appears as the English term with the Italian term in parentheses
  **at first use only** — `service ticket (Intervento)` in TEC-001, then plain `service ticket`
  everywhere after, including in CAP-001.
- All descriptive prose — Target, Main Flow, Variations, User Story — is fully English.

### Source Requirement

"Il sistema gestisce le manutenzioni degli impianti. Un Tecnico apre un intervento e ne registra
le ore lavorate. Un Capoarea approva gli interventi chiusi. Ogni intervento approvato genera un
report per il cliente."

### Role Identifier Legend (as it appears in the English deliverable)

- **TEC** = Technician
- **CAP** = Area Supervisor
- **SYS** = System

### Extracted Use Cases

**Role: Technician (TEC)**

A field engineer who carries out maintenance on the customer's plants (impianti). The technician owns the
record of the work done and the time spent on it, and has no authority to approve it.

#### Use Case TEC-001: Open Service Ticket

**Code**: TEC-001

**Name**: Open Service Ticket

**Title**: TEC-001: Open Service Ticket

**Priority**: High

**Target**: Enable a technician to open a service ticket (Intervento) for a plant that needs maintenance and to record the hours worked (ore lavorate) against it. The ticket is the unit the rest of the process runs on: both the approval and the customer report hang off it. Recorded hours feed the customer's invoice and the plant's maintenance history alike. A ticket stays open until the technician closes it, so work spanning several days accumulates on one record.

**Main Flow**:
1. Technician selects the plant and opens a new service ticket
2. System assigns the ticket number and records the opening technician and timestamp
3. Technician records the hours worked and the work performed
4. Technician closes the ticket
5. System places the closed ticket in the area supervisor's approval queue

**Variations**:
- **1a. Plant not registered**: system refuses the ticket and asks for the plant to be registered first
- **3a. Hours exceed the shift length**: system asks the technician to confirm them or split them across days

**Input Data**:

*Mandatory*:
- Technician credentials
- Plant identifier
- Fault description
- Hours worked
- Work performed

*Optional*:
- Spare parts used
- Photographs of the fault
- Second technician on site

**Output Data**:
- Service ticket number
- Open ticket record
- Hours entry on the plant's maintenance history
- Closed ticket in the area supervisor's approval queue
- Spare-parts consumption record
- Confirmation to the technician

**Dependencies**:
- CAP-001: Approve Closed Service Ticket (workflow sequence)

**Source**: «Un Tecnico apre un intervento e ne registra le ore lavorate»

**User Story**: As a technician, I want to open a service ticket and record my hours against it, so that the work is approved and billed from a single record.

**Acceptance Criteria**:
1. Given a registered plant, when the technician opens a service ticket and records hours worked, then the ticket carries a number and the hours appear on the plant's maintenance history
2. Given an unregistered plant, when the technician tries to open a ticket, then the ticket is refused and registration is requested

**Role: Area Supervisor (CAP)**

The manager responsible for a geographic area's maintenance work. The area supervisor checks the
technicians' closed tickets and decides whether the recorded time may be billed.

#### Use Case CAP-001: Approve Closed Service Ticket

**Code**: CAP-001

**Name**: Approve Closed Service Ticket

**Title**: CAP-001: Approve Closed Service Ticket

**Priority**: Medium

**Target**: Let an area supervisor approve the closed service tickets waiting in their queue, so the recorded hours become billable. Approval is the gate the customer report depends on: no report leaves before it.

**Main Flow**:
1. Area supervisor opens the approval queue and selects a closed service ticket
2. System shows the recorded hours, the work performed, and the spare parts used
3. Area supervisor approves the ticket, and the system triggers the customer report

**Variations**:
- **3a. Hours disputed**: area supervisor returns the ticket to the technician with a reason, and it leaves the queue

**Input Data**:

*Mandatory*:
- Area supervisor credentials
- Closed ticket number
- Recorded hours and work performed

*Optional*:
- Approval note

**Output Data**:
- Approved ticket status
- Billable hours release
- Customer report generation trigger
- Notification to the opening technician

**Dependencies**:
- TEC-001: Open Service Ticket (prerequisite)
- SYS-001: Generate Customer Report (triggering)

**Source**: «Un Capoarea approva gli interventi chiusi»

**User Story**: As an area supervisor, I want to approve closed service tickets, so that only checked hours reach the customer's invoice.

No Acceptance Criteria: this use case is Medium priority, and the field belongs to High-priority
use cases only.
