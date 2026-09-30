# OOMKilled / memory pressure

Symptoms: pods restarting with reason OOMKilled, memory usage near limit.

Diagnostics (read-only):
1. `kubectl get pods -n <ns> | grep -i oom`
2. `kubectl describe pod <pod> -n <ns>` (check Last State and limits)
3. Check memory trend in Datadog for the last 24h / latest deploy.

Mitigation: roll back the last deploy if memory grew after it; otherwise raise the memory limit via the Helm values PR and investigate leaks.
