# Requirements traceability

This implementation follows the functional and non-functional requirements in
`SRS/SRS_v2.pdf`. The dashboard is the integration layer; it does not replace
the independently testable module interfaces.

| Requirement | Implemented in | Verification |
| --- | --- | --- |
| REQ-01 to REQ-04: start/stop, CPU/RAM, processes, automatic refresh | `monitoring/performance_monitor.py`, `dashboard.py` | `tests/test_performance_monitor.py` and dashboard smoke/compile check |
| REQ-05 to REQ-08, REQ-20 to REQ-21: cautious suspected-throttling detection, alerts, recommendations | `detection/detector.py`, `dashboard.py` | `tests/test_detector.py` |
| REQ-09 to REQ-12: process listing, eligibility, confirmation, result | `optimization/process_analyzer.py`, `optimization/optimization_engine.py`, `dashboard.py` | `tests/test_optimization.py`, `tests/test_priority_adapter.py` |
| REQ-13 to REQ-15: monitoring-period network metrics and threshold alerts | `monitoring/network_monitor.py`, `dashboard.py` | `tests/test_network_monitor.py` |
| REQ-16 to REQ-19: predefined/selectable/editable active profiles | `optimization/profiles.py`, `dashboard.py` | `tests/test_profiles.py` |
| REQ-22 to REQ-23: timestamped event/action logs and recent-log view | `logging_module/event_logger.py`, `dashboard.py` | `tests/test_event_logger.py` |

## Non-functional coverage

- Safety: protected process deny-list, explicit confirmation, saved original
  priorities, and safe OS-error handling are enforced by the optimization
  engine.
- Privacy: the performance monitor uses only aggregate host metrics and public
  process metadata. Network monitoring uses aggregate counters only.
- Responsiveness and overhead: the dashboard requests non-blocking `psutil`
  samples at a defined one-second cadence; it limits the visible process list.
- Maintainability and portability: OS-specific scheduling priority calls are
  isolated in `optimization/priority_adapter.py`.
- Security/quality: Jenkins compiles and tests every build before a main-branch
  package may be deployed.
