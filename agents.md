# Multi-Agent Coordination Specification

                         +-----------------------------+
                         |     Incoming Check-In       |
                         |  (Valence + Text + Voice)   |
                         +--------------+--------------+
                                        |
                                        v
                         +-----------------------------+
                         |  Safety & Ingestion Guard   |
                         +--------------+--------------+
                                        |
                 +----------------------+----------------------+
                 | (Explicit Danger Pattern)                   | (Standard Processing)
                 v                                             v
  +------------------------------+              +------------------------------+
  |    Crisis Intercept Agent    |              |   Linguistic Profiling Agent |
  +--------------+---------------+              +--------------+---------------+
                 |                                             |
                 v                                             v
  +------------------------------+              +------------------------------+
  |  Emergency Dispatch & Lock   |              |   Trajectory Velocity Agent  |
  +------------------------------+              +--------------+---------------+
                                                               |
                                                               v
                                                +------------------------------+
                                                |   HITL Coordinator Agent     |
                                                +------------------------------+

### 1. Safety & Ingestion Guard (`guard_agent`)
- **Execution**: Flask ingress filter on check-in submissions.
- **Responsibility**: Verifies client consent status and scans raw strings against acute self-harm expressions.
- **Routing**: If flagged, halts standard NLP scoring and immediately diverts execution to `agent_crisis_intercept`.

### 2. Linguistic Profiling Agent (`nlp_agent`)
- **Execution**: Asynchronous or synchronous NLP evaluation worker.
- **Responsibility**: Tokenizes journal inputs, calculates first-person pronoun density, assesses absolutist distortion counts, and parses mock acoustic metadata from voice notes.

### 3. Trajectory Velocity Agent (`trajectory_agent`)
- **Execution**: Rolling state analysis engine.
- **Responsibility**: Compares current scores against the user's historical 7-day baseline to calculate slope (ΔDPI). Flags rapid multi-day declines and updates user risk classifications.

### 4. Crisis Intercept Agent (`crisis_agent`)
- **Execution**: Real-time event handler for high-severity inputs.
- **Responsibility**: Locks user interface into crisis mode, activates the 4-7-8 breathing pacer, displays national helplines (Tele-MANAS, KIRAN, 988), and marks the active case as SEV-1.

### 5. HITL Coordinator Agent (`hitl_agent`)
- **Execution**: Counselor triage controller.
- **Responsibility**: Populates flagged moderate and critical profiles into the Counselor Review Queue, generates isolated Jitsi video consultation links (`AegisMind-Case-<ID>`), and moderates flagged submissions in the Anonymous Peer Forum.