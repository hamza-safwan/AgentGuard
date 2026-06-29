# Mock Tools

The mock tool server gives agents deterministic API responses during tests.

## Start the Server

```bash
python -m agentguard.tool_runtime.server
```

By default it binds to port `8100`.

## Built-In Tools

AgentGuard includes mock tools for:

- CRM/customer profile lookup.
- Email sending.
- Refund/payment behavior.
- Calendar actions.
- Browser/search behavior.
- Policy document retrieval.
- Permission checks.

## Scenario-Scoped Mocks

```yaml
mocks:
  - name: issue_refund
    when:
      args.amount: { lte: 100 }
    response:
      status: success
      refund_id: ref_demo_1

  - name: issue_refund
    when:
      args.amount: { gt: 100 }
    response:
      status: blocked
      reason: manager approval required
```

When a scenario registers mocks, AgentGuard attaches `X-AgentGuard-Scope` to adapter calls so the mock server can isolate responses per scenario.

## Strict Mode

Without strict mode, unregistered scoped calls can fall back to the global catalog.

With strict mode:

```bash
agentguard run scenarios --mock-strict
```

Unregistered scoped tool calls return `424 Failed Dependency`. This is useful when you want to catch unexpected tool use.

## Custom Mock Catalogs

Plugins can register mock catalogs:

```toml
[project.entry-points."agentguard.mock_tools"]
billing = "acme.agentguard.mocks:CATALOG"
```

```python
from agentguard.tool_runtime.catalog import MockCatalog

def lookup_invoice(invoice_id: str) -> dict:
    return {"invoice_id": invoice_id, "status": "paid"}

CATALOG = MockCatalog(dynamic={"lookup_invoice": lookup_invoice})
```

