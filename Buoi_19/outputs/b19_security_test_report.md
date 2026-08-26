# Security & Local Guardrail Test Report - Buoi 19

The tests verify the configured Ollama-only prompt path, RBAC data filtering, output guardrails, audit redaction, and a local model invocation.

| Test | Status | Detail |
|---|---|---|
| local prompt routing | PASS | provider=ollama; base_url=http://localhost:11434; Ollama branch present=True |
| RBAC Staff exclusion | PASS | restricted_chunks=393; leaked_chunks=0 |
| citation integrity | PASS | uc3=True; uc4=True |
| human review guardrail | PASS | uc3_rows=2; uc4_rows=6 |
| audit log privacy | PASS | events=15; configured_secret_values_absent=True; unredacted_assignments=False |
| local model resilience | PASS | exit_code=0; response_received=True; model runs from persistent local volume |

## Infrastructure Note

The application is configured to send prompts only to the local Ollama endpoint while `LLM_PROVIDER=ollama`. Docker's standard bridge network remains enabled to preserve host access to Streamlit and model-management operations; a physically air-gapped deployment requires host firewall or network-policy enforcement outside this Compose file.

```text
SECURITY TESTS: PASS
PASSED: 6
FAILED: 0
```
