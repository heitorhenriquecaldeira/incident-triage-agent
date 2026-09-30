# High latency / 5xx errors

Symptoms: p95 latency or error rate above SLO.

Diagnostics (read-only):
1. Datadog APM: identify slowest endpoint and downstream dependency.
2. Check database connections and slow queries; check Redis hit rate.
3. `kubectl top pods -n <ns>` for CPU throttling; check HPA status.

Mitigation: scale out, roll back recent deploy, or fail over the dependency.
