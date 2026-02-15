# Kiro - AWS Hackathon Submission

## Project Overview

**Project Name:** VeriGov AI  
**Team Name:** [Newsbot]  
**Submission Date:** February 12, 2026

## Problem Statement

Trust in public institutions is collapsing due to widespread misinformation and misunderstanding of government policies. Citizens struggle to access accurate information directly from official sources, instead relying on third-party interpretations that may be biased, incomplete, or deliberately misleading. Government policies are frequently misrepresented across social media and news outlets, creating confusion and eroding public confidence. There is a critical need for a platform that exclusively uses government-affiliated sources to distribute verified information and combat misinformation at its root.

## Solution

VeriGov AI is an official-source-only verification platform that delivers authenticated government, defence, and global updates in real time. Unlike general-purpose AI platforms that scrape the open internet indiscriminately, our system ingests data exclusively from trusted, verified government and institutional data pipelines. We propose an AI-powered Fact Checking and Authenticity Module designed specifically for public systems and communities, which verifies, corrects, and updates news using only official, authoritative sources.

### How It Works: Collect → Verify → Structure → Deliver

1. **Collect** updates from trusted official sources
2. **Verify** claims across multiple authorities
3. **Structure** policies into summaries, changes & impact
4. **Deliver** real-time authenticated insights to users



### System Components

**1. Data Collection & Ingestion Layer**
- **Whitelisted Web Scraping:** Only from verified government domains
- **Official API Integration:** Direct connections to government APIs
- **Trusted Sources:**
  - Government portals
  - Ministry websites
  - Judiciary systems
  - Defence departments
  - International organizations
- **Tools:** Python-based data collection pipelines
- No unofficial sources enter the system

**2. Fact Verification Engine (Core)**
- **Claim Matching:** Matches user claims with official documents
- **Semantic Validation:** AI-powered semantic analysis for context understanding
- **Timeline-Based Validation:** Verifies claims against historical policy timelines
- **Multi-Authority Cross-Verification:** Claims verified across multiple official authorities
- **Confidence Scoring:** Every piece of information receives a confidence score
- **Instant Flagging:** Unverified claims are flagged immediately

**3. Trusted Source Validation (Core USP)**
- **Verified Domains Only:** Only verified government domains and official handles accepted
- **Rule-Based Trust Filtering:** Automated filtering ensures source authenticity
- **Optional Audit Logging:** Complete traceability of verification process
- **Zero Unofficial Sources:** Strict validation prevents contamination from unreliable sources

**4. Update & Change Detection System**
- **Policy Monitoring:** Detects changes in government policies
- **Law Updates:** Tracks amendments and new legislation
- **Conflict Detection:** Identifies contradictions in official statements
- **Outdated Information Flagging:** Automatically flags superseded information
- **Real-Time Alerts:** Notifies users of critical updates

**5. Frontend & Visualization Dashboard**
- **User-Friendly Interface:** Intuitive verification dashboard
- **Clear Labeling System:**
  - ✓ Verified (confirmed by official sources)
  - ⚠ Partially Verified (partial confirmation)
  - ✗ Incorrect (contradicts official sources)
- **Real-Time Updates:** Live feed of authenticated information
- **Misinformation Warnings:** Instant alerts for false claims

**6. Explainability & Citations Module**
- **Official Source Links:** Direct links to government sources for every claim
- **Transparent Mapping:** Clear claim-to-source traceability
- **Citation Generation:** Automatic citation formatting
- **Audit Trail:** Complete verification history for transparency



## Key Features

### 1. Trusted Collection
- **Official-Source-Only Ingestion:** Exclusively collects from government portals, judicial bodies, defence ministries, international organizations, and Tier-1 agencies
- **Zero Unofficial Sources:** No third-party or internet sources enter the system
- **Continuous Monitoring:** Real-time data ingestion from verified pipelines

### 2. Automated Fact Authentication
- **Atomic Fact Breakdown:** Each claim is decomposed into verifiable atomic facts
- **Multi-Authority Cross-Verification:** Claims verified across multiple official authorities
- **Confidence Scoring:** Every piece of information receives a confidence score
- **Instant Flagging:** Unverified claims are flagged immediately

### 3. Structured Intelligence
- **Clear Summaries:** Complex policies converted into understandable summaries
- **Policy Change Tracking:** Side-by-side comparisons of policy updates
- **Impact Analysis:** Explains real-world impact of government decisions
- **Timeline Tracking:** Historical context and progression of policies

### 4. Real-Time Delivery
- **Verified Alerts:** Push notifications for authenticated updates
- **Fact-Checked News:** All news verified against official sources
- **Misinformation Warnings:** Instant alerts when false claims are detected
- **Transparent Source Links:** Direct links to official government sources
- **Unified Dashboard:** Single interface for all authenticated information


## Kiro Integration

Kiro played a crucial role in accelerating the development of VeriGov AI:

- **AI-Assisted Development:** Used Kiro's intelligent code suggestions to rapidly build the fact authentication engine and data ingestion pipelines
- **AWS Service Integration:** Leveraged Kiro to seamlessly configure and deploy AWS services with best practices for real-time processing
- **Multi-Source Integration:** Built complex integrations with government APIs and data sources efficiently with Kiro's assistance
- **Automated Testing:** Created comprehensive test suites to ensure verification accuracy across multiple authorities
- **Documentation Generation:** Utilized Kiro to maintain clear documentation for the authentication algorithms and data flows
- **Code Optimization:** Applied Kiro's recommendations to optimize performance for real-time fact-checking at scale
- **Debugging Support:** Quickly identified and resolved issues in the cross-verification logic with Kiro's diagnostic capabilities

## Technical Implementation

### Technology Stack

**Backend:**
- Python for data collection and processing pipelines
- Fact verification engine with semantic and timeline-based validation
- Rule-based trust filtering system

**Frontend:**
- User-friendly verification dashboard
- Real-time visualization of verification results
- Interactive labeling system (Verified / Partially Verified / Incorrect)

**Data Processing:**
- Whitelisted web scraping from government domains
- Official API integrations
- Semantic analysis for claim matching
- Timeline-based validation engine

**Core Features:**
- Trusted source validation (Core USP)
- Update and change detection
- Explainability and citation generation
- Audit logging for transparency




## Team Members

- **[Shraddha Kulkarni]** - [Team Leader]
- **[Ashutosh Deshpande]** - [Team Member]



## Conclusion

VeriGov AI addresses the critical crisis of collapsing public trust by creating a direct bridge between citizens and official government sources. By exclusively using verified government, defence, and institutional data pipelines—and eliminating all unofficial sources—we ensure citizens receive accurate, authenticated information about policies and official statements. Our four-stage process (Collect → Verify → Structure → Deliver) transforms complex government updates into understandable, fact-checked insights delivered in real time. VeriGov AI doesn't just fight misinformation—it rebuilds trust by providing transparency, multi-authority verification, and direct access to the truth. This platform demonstrates how AI can restore confidence in public institutions and create an informed citizenry that understands government policies correctly, straight from official sources.
