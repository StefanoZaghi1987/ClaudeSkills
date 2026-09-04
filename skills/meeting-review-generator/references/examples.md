# Examples

Concrete examples of well-formatted meeting review report components.

Section titles below are English for reference; write them in the report's language (see `output-structure.md`).

---

## Example 1: High Relevance Theme

### Theme Title: Cloud Infrastructure Migration Strategy

The team extensively discussed the strategy for migrating the company's on-premises infrastructure to AWS cloud services. This initiative is critical for scaling operations and reducing long-term infrastructure costs. The migration will be executed in three phases over six months, starting with non-production environments.

The technical approach involves using AWS Migration Hub to orchestrate the move of approximately 150 virtual machines and 50 database instances. The team agreed to adopt a "lift and shift" strategy for Phase 1, focusing on minimal changes to applications during migration, followed by optimization in subsequent phases. Key technical requirements include maintaining 99.9% uptime during migration, implementing automated backup systems, and establishing monitoring through AWS CloudWatch.

During the discussion, several migration approaches were evaluated. The team considered rehosting (lift-and-shift), replatforming (lift-tinker-and-shift), and complete refactoring. After analyzing cost, timeline, and risk factors, the team determined that starting with rehosting provides the fastest time-to-value while minimizing initial risk exposure. Refactoring will be addressed in Phase 3 after gaining operational experience with the cloud environment.

**Decision**: The migration will use AWS as the cloud provider, following a three-phase approach beginning with lift-and-shift rehosting.

**Decision**: Phase 1 will target the development and staging environments, scheduled for completion by Q2 2024.

**Decision**: A dedicated cloud infrastructure team of four engineers will be established to manage the migration and subsequent operations.

**Open Point**: The disaster recovery strategy for the cloud environment requires further architectural review and will be discussed in a dedicated session next week.

**Open Point**: Cost optimization strategies for reserved instances vs. on-demand pricing need detailed financial analysis before Phase 2.

**Action**: **Marco Rossi** will complete the detailed migration plan document, including timeline, resource allocation, and risk mitigation strategies by March 30, 2024.

**Action**: **Sarah Chen** will conduct vendor negotiations with AWS for enterprise support and establish the account structure by April 5, 2024.

**Action**: **IT Security team** will review and update security policies to address cloud-specific requirements, including IAM roles and data encryption standards, by April 15, 2024.

**Dependencies**: This theme depends on the Budget Approval theme, as migration costs must be confirmed before proceeding. Additionally, the Security Compliance Review theme must be completed before Phase 1 execution begins.

**Risk**: Migration timing overlaps with peak business season (Q2), potentially creating resource conflicts. Mitigation: Establish clear communication protocols and rollback procedures.

**Priority**: Critical - This is a strategic initiative with executive visibility and Q2 deadlines.

**Constraint**: AWS region selection is limited to EU-Central-1 due to data residency regulations under GDPR.

---

## Example 2: Medium Relevance Theme

### Theme Title: Employee Onboarding Process Updates

The HR team presented proposed changes to the employee onboarding process based on feedback from recent new hires. The updated process aims to reduce time-to-productivity from six weeks to four weeks by implementing a structured buddy system and pre-boarding activities.

Key changes include sending equipment and access credentials to new employees one week before their start date, assigning experienced team members as onboarding buddies for the first 30 days, and creating role-specific onboarding checklists. The team reviewed feedback from the last quarter showing that 40% of new employees felt overwhelmed in their first two weeks, indicating need for better structure and support.

**Decision**: The new onboarding process will be piloted with the next cohort of five employees starting in April 2024.

**Action**: **HR Department** will develop the onboarding buddy guidelines and training materials by March 25, 2024.

**Action**: **IT team** will implement the pre-boarding access credential system to enable week-before account activation.

**Dependencies**: This initiative requires coordination with the IT Infrastructure team for technical onboarding components.

---

## Example 3: Low Relevance Theme

### Theme Title: Office Parking Policy Reminder

The facilities team reminded attendees about the updated parking policy taking effect next month. Reserved spots will be assigned on a quarterly rotation basis, and the new parking permit system will require badge scanning for entry. No immediate actions are required from the project team, but team members were encouraged to review the policy document distributed via email.

---

## Example 4: Summary Section

### 3. SUMMARY

#### 3.1 Decisions Recap

- **Decision**: The cloud infrastructure migration will use AWS as the provider, following a three-phase approach beginning with lift-and-shift rehosting. (Related to: Cloud Infrastructure Migration Strategy)

- **Decision**: Phase 1 of the cloud migration will target development and staging environments, scheduled for completion by Q2 2024. (Related to: Cloud Infrastructure Migration Strategy)

- **Decision**: A dedicated cloud infrastructure team of four engineers will be established. (Related to: Cloud Infrastructure Migration Strategy)

- **Decision**: The Q1 budget allocation will include an additional €50,000 for cloud migration planning and vendor negotiations. (Related to: Budget Approval)

- **Decision**: The new employee onboarding process will be piloted with the next cohort of five employees starting in April 2024. (Related to: Employee Onboarding Process Updates)

#### 3.2 Open Points List

- **Open Point**: The disaster recovery strategy for the cloud environment requires further architectural review and will be discussed in a dedicated session next week. (Related to: Cloud Infrastructure Migration Strategy)

- **Open Point**: Cost optimization strategies for reserved instances vs. on-demand pricing need detailed financial analysis before Phase 2. (Related to: Cloud Infrastructure Migration Strategy)

- **Open Point**: Final approval from legal department on data processing agreements with AWS is pending. (Related to: Security Compliance Review)

#### 3.3 Actions Overview

- **Action**: **Marco Rossi** will complete the detailed cloud migration plan document by March 30, 2024. (Related to: Cloud Infrastructure Migration Strategy)

- **Action**: **Sarah Chen** will conduct vendor negotiations with AWS and establish account structure by April 5, 2024. (Related to: Cloud Infrastructure Migration Strategy)

- **Action**: **IT Security team** will review and update security policies for cloud requirements by April 15, 2024. (Related to: Cloud Infrastructure Migration Strategy)

- **Action**: **Finance Department** will prepare cost-benefit analysis for cloud migration including 3-year TCO by April 1, 2024. (Related to: Budget Approval)

- **Action**: **HR Department** will develop onboarding buddy guidelines and training materials by March 25, 2024. (Related to: Employee Onboarding Process Updates)

- **Action**: **IT team** will implement pre-boarding access credential system for new employees. (Related to: Employee Onboarding Process Updates)

#### 3.4 Critical Aspects

**Risks**:
- Migration timing overlaps with peak business season (Q2), potentially creating resource conflicts. Mitigation through clear communication protocols and rollback procedures is essential.
- Potential vendor lock-in with AWS may limit future flexibility. Team will design architecture with portability considerations.

**Priorities**:
- Cloud migration is a critical strategic initiative with executive visibility and firm Q2 deadlines.
- Security compliance review must be completed before Phase 1 execution - non-negotiable requirement.

**Constraints**:
- AWS region selection limited to EU-Central-1 due to GDPR data residency regulations.
- Budget approval cycle requires all expenditures above €100,000 to go through board review, potentially delaying Phase 2.

#### 3.5 Overall Progress

Since the January 2024 meeting, significant progress has been achieved on the technology stack evaluation. The team has narrowed cloud provider options from five to one (AWS) based on comprehensive technical and cost analysis. The budget approval process has advanced through initial stakeholder reviews and is now awaiting final finance department sign-off. Employee onboarding improvements, initially discussed as informal feedback, have now been formalized into a structured pilot program with clear success metrics.

---

## Example 5: Follow-Up Section

### 4. FOLLOW-UP

#### Cloud Infrastructure Migration Actions

1. **Marco Rossi**: Complete detailed cloud migration plan document
   - Deadline: March 30, 2024
   - Related to: Cloud Infrastructure Migration Strategy
   - Dependencies: Requires finalized budget allocation from Finance
   - Priority: High
   - Success criteria: Document includes timeline, resource allocation, risk mitigation strategies, and phase-by-phase execution plan approved by CTO

2. **Sarah Chen**: Conduct AWS vendor negotiations and establish account structure
   - Deadline: April 5, 2024
   - Related to: Cloud Infrastructure Migration Strategy
   - Dependencies: Legal approval of data processing agreements
   - Priority: High
   - Success criteria: Enterprise support agreement signed, AWS Organization structure created with appropriate account hierarchy

3. **IT Security team**: Review and update security policies for cloud requirements
   - Deadline: April 15, 2024
   - Related to: Cloud Infrastructure Migration Strategy and Security Compliance Review
   - Dependencies: AWS account structure must be established
   - Priority: Critical
   - Success criteria: Updated policies covering IAM roles, data encryption standards, network security, and compliance requirements approved by CISO

#### Budget and Financial Actions

4. **Finance Department**: Prepare comprehensive cost-benefit analysis for cloud migration
   - Deadline: April 1, 2024
   - Related to: Budget Approval
   - Dependencies: Vendor pricing from Sarah Chen's negotiations
   - Priority: High
   - Success criteria: Analysis includes 3-year Total Cost of Ownership (TCO), ROI projections, and cash flow impact approved by CFO

#### HR and Onboarding Actions

5. **HR Department**: Develop onboarding buddy guidelines and training materials
   - Deadline: March 25, 2024
   - Related to: Employee Onboarding Process Updates
   - Dependencies: None
   - Priority: Medium
   - Success criteria: Guidelines document, buddy training presentation, and role-specific checklists ready for April cohort

6. **IT team**: Implement pre-boarding access credential system
   - Deadline: March 22, 2024 (before first April new hire)
   - Related to: Employee Onboarding Process Updates
   - Dependencies: None
   - Priority: Medium
   - Success criteria: Automated system enables account activation one week before start date, tested with dummy account

---

## Example 6: Introduction Section

### 1. INTRODUCTION

On March 15, 2024, the Technology Leadership Team met to review progress on the Q1 2024 strategic initiatives and make key decisions regarding the cloud infrastructure migration project. Participants included Marco Rossi (CTO), Sarah Chen (VP of Engineering), members of the IT Infrastructure team, Finance Department representatives, and HR leadership.

The meeting's primary objective was to finalize the cloud migration strategy, secure budget approval for the initiative, and address operational improvements in employee onboarding based on recent feedback. The discussion covered technical architecture decisions, vendor selection, timeline planning, budget allocation, risk assessment, and dependency mapping across multiple organizational functions.

This report provides a comprehensive analysis of the themes discussed, documents all decisions made, tracks action items assigned to responsible parties, and identifies open points requiring further discussion.

---

## Example 7: Multiple Format Variations for Actions

### Table Format (Useful when many similar actions)

| Action | Assignee | Deadline | Priority | Related Theme |
|--------|----------|----------|----------|---------------|
| Complete migration plan | **Marco Rossi** | Mar 30, 2024 | High | Cloud Migration |
| AWS vendor negotiations | **Sarah Chen** | Apr 5, 2024 | High | Cloud Migration |
| Update security policies | **IT Security** | Apr 15, 2024 | Critical | Security Compliance |
| Cost-benefit analysis | **Finance** | Apr 1, 2024 | High | Budget Approval |
| Onboarding guidelines | **HR Team** | Mar 25, 2024 | Medium | Onboarding Updates |

### Grouped by Priority Format

#### High Priority Actions

1. **Marco Rossi**: Complete detailed cloud migration plan document (Deadline: March 30, 2024)
   - Must include timeline, resource allocation, and risk mitigation strategies
   - Dependencies: Finalized budget allocation from Finance

2. **Sarah Chen**: Conduct AWS vendor negotiations and establish account structure (Deadline: April 5, 2024)
   - Requires legal approval of data processing agreements
   - Critical for enabling Phase 1 execution

#### Medium Priority Actions

3. **HR Department**: Develop onboarding buddy guidelines and training materials (Deadline: March 25, 2024)
   - No blockers, can proceed immediately
   - Needed for April new hire cohort

### Grouped by Theme Format

#### Cloud Infrastructure Migration Strategy

- **Marco Rossi**: Complete detailed migration plan (Due: March 30, 2024) - High Priority
- **Sarah Chen**: AWS vendor negotiations and account setup (Due: April 5, 2024) - High Priority
- **IT Security team**: Update security policies for cloud (Due: April 15, 2024) - Critical Priority

#### Budget Approval

- **Finance Department**: Prepare cost-benefit analysis with 3-year TCO (Due: April 1, 2024) - High Priority

#### Employee Onboarding Process Updates

- **HR Department**: Develop buddy guidelines and materials (Due: March 25, 2024) - Medium Priority
- **IT team**: Implement pre-boarding credential system (Due: March 22, 2024) - Medium Priority

---

## Example 8: Dependency Mapping Language

### Explicit Dependency Statements

"The Cloud Infrastructure Migration theme depends on completion of the Budget Approval theme, as migration costs must be confirmed before proceeding with vendor contracts."

"This action is blocked by the Security Compliance Review, which must complete its assessment before Phase 1 can begin execution."

"The Employee Onboarding Process Updates theme requires coordination with the IT Infrastructure theme to implement the pre-boarding access system."

### Cross-Reference Examples

"See the Cloud Infrastructure Migration Strategy theme for detailed technical requirements that inform this budget request."

"As discussed in the Security Compliance Review section, data residency regulations constrain our AWS region selection."

"This decision builds on the vendor evaluation completed in the January 2024 meeting (see previous meeting report for analysis details)."

---

## Example 9: Language Variations

### Italian Example (Decisions)

**Decisione**: La migrazione dell'infrastruttura cloud utilizzerà AWS come provider, seguendo un approccio in tre fasi che inizia con la strategia lift-and-shift.

**Decisione**: La Fase 1 della migrazione cloud si concentrerà sugli ambienti di sviluppo e staging, con completamento previsto entro Q2 2024.

**Punto aperto**: La strategia di disaster recovery per l'ambiente cloud richiede un'ulteriore revisione architetturale e sarà discussa in una sessione dedicata la prossima settimana.

**Azione**: **Marco Rossi** completerà il documento di piano di migrazione dettagliato entro il 30 marzo 2024.

### English Example (Decisions)

**Decision**: The cloud infrastructure migration will use AWS as the provider, following a three-phase approach beginning with lift-and-shift rehosting.

**Decision**: Phase 1 of the cloud migration will target development and staging environments, scheduled for completion by Q2 2024.

**Open Point**: The disaster recovery strategy for the cloud environment requires further architectural review and will be discussed in a dedicated session next week.

**Action**: **Marco Rossi** will complete the detailed migration plan document by March 30, 2024.
