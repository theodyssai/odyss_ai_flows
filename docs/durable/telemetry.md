# Telemetry

The durable plugin includes optional OpenTelemetry tracing.

Tracing is disabled by default. When enabled, spans are emitted for node activities, direct flow activities, and subflow boundaries.

---

# Enabling Telemetry

Add to `global_config.json`:

```json
{
  "durable": {
    "telemetry": {
      "enabled": true
    }
  }
}
```

The setting is read lazily at the start of each activity. Changing it takes effect on the next invocation without redeployment.

Your application is responsible for configuring an OpenTelemetry exporter. The plugin emits spans only — it does not configure exporters, resource attributes, or SDK initialization.

---

# What Is Instrumented

| Span name | Trigger |
|---|---|
| `durable.activity:node:<flow>:<node>` | Each node activity execution |
| `durable.activity:direct:<flow>` | Each direct flow activity execution |
| `durable.subflows_level:<depth>` | Each level of nested subflow dispatch |

Spans carry the following attributes where applicable:

| Attribute | Description |
|---|---|
| `durable.node` | Node name |
| `durable.flow_name` | Flow name |
| `durable.kind` | `direct` for direct flow activities |
| `durable.instance_id` | Orchestration instance ID (subflow spans) |
| `durable.subflows_depth` | Nesting level (subflow spans) |

If an activity raises an exception, it is recorded on the span before propagating.

---

# Trace Propagation

Azure Durable Functions activities and orchestrators run as separate worker invocations. Standard in-process context propagation does not cross these boundaries automatically.

The plugin propagates trace context explicitly through inputs. When telemetry is enabled, the current span's `traceparent` is written into `base_inputs["_traceparent"]` and threaded through all subsequent activities and sub-orchestrators.

Each activity reads `_traceparent` from its inputs, reconstructs the parent context, and starts its span as a child of that context.

This makes the entire execution — across all activities, orchestrators, and workers — appear as a single connected trace in your telemetry backend.

---

# Virtual Spans

Azure Durable Functions orchestrators must be deterministic. Orchestrator code replays from the beginning every time a new event arrives, so creating real spans inside orchestrator code would produce different span IDs and timings on each replay.

To preserve trace continuity at subflow boundaries without violating determinism, the plugin creates a virtual span inside a dedicated activity (`build_virtual_span`). This activity:

1. Receives the current `_traceparent`.
2. Creates a new span as a child of that context.
3. Extracts and returns the new `traceparent`.

The returned `traceparent` is then injected into the subflow's `base_inputs`. All activities within the subflow level become children of this virtual span.

The resulting trace hierarchy reflects the subflow nesting:

```
parent flow
└── durable.subflows_level:0
    ├── subflow A
    │   └── durable.activity:node:...
    └── subflow B
        └── durable.subflows_level:1
            └── sub-subflow C
```

---

# Performance

When telemetry is disabled, each activity performs a single async config read and then calls the underlying logic directly. There is no span creation, context extraction, or propagation overhead.
