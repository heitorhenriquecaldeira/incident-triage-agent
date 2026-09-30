# CrashLoopBackOff

Symptoms: pod repeatedly failing to start.

Diagnostics (read-only):
1. `kubectl logs <pod> -n <ns> --previous`
2. `kubectl describe pod <pod> -n <ns>` (events, probes, image)
3. Check for missing ConfigMap/Secret or failing readiness/liveness probes.

Mitigation: roll back to the previous image tag; fix config and redeploy.
