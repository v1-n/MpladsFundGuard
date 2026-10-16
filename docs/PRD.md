# MPLADS FundGuard — Product Requirements Document (PRD)

## 1. Product Overview
**MPLADS FundGuard** is an open, reproducible, and privacy-preserving public procurement screening platform for the Members of Parliament Local Area Development Scheme (MPLADS) in India.
- **Problem Statement ID:** 26102 (MoSPI)
- **Department:** Data Informatics & Innovation Division (DIID), Ministry of Statistics and Programme Implementation (MoSPI)

## 2. Target Users
1. **Auditors & Oversight Officials:** State and central auditors performing manual field audits and sample inspection.
2. **Civic Data Researchers & Journalists:** Analysts examining civic spending efficiency, project stall rates, and contractor concentration.
3. **Citizen Stakeholders:** Members of the public reviewing local civic development expenditures in their respective constituencies.

## 3. Goals & Objectives
- **Screening, Not Accusation:** Provide exploratory review priority rankings without alleging fraud, assigning guilt, or generating MP leaderboards.
- **Ledger Integrity Assurance:** Detect 8 canonical deterministic ledger irregularities (e.g. duplicate payments, same-day bulk splits, ghost completions, stalled allocations).
- **Stratified Multi-Dimensional Screening:** Score projects against localized peer cohorts (Category × State) using an ensemble of Isolation Forests across multiple random seeds.
- **Traceable Dossiers:** Surface observed public ledger evidence, statistical deviations, and deterministic flags in an integrated investigation view.
- **Double-Blind Manual Audit Protocol:** Support unbiased manual review with SMD-matched controls (50 top outliers vs 50 matched controls) and secure reviewer session isolation.

## 4. Out of Scope (Explicit Non-Goals)
- **Automated Accusations:** System never outputs "fraud probability", "culprit", or "fraud score".
- **MP / Constituency Blame Rankings:** No competitive leaderboards ranking MPs or constituencies by suspicion.
- **Rajya Sabha Data:** Focused strictly on 18th Lok Sabha (543 MPs).