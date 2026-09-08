# Durable scenario inventory

19 scenarios (8 infra-free + 11 live). Consolidated from the original scenarios and the
`durable_handson` matrix — each merged scenario runs several orchestrations / assertion
blocks. Verdicts below are **keep** unless noted; redundant shapes are deliberately tested
once at the strongest applicable layer.

`§N` refers to the verified-behavior findings in `../../../../durable_handson/PACKAGE_ASSESSMENT.md`
and the durable test plan; a "characterization pin" asserts a **known defect's current
behavior**, so fixing the package will make it fail deliberately.

## Infra-free — no host; gated only on the plugin being installed

| Scenario | Verdict | What it covers / why |
|---|---|---|
| `direct_flow_execution` | **keep** | Compares core `run_flow` with the plugin's no-executor `run_durable_flow` path. This used to call core only and therefore did not test the durable plugin; it now pins transparent pass-through behavior. |
| `unit_build_dag` | **keep** | `build_dag` static scan: node discovery, `__init__.py` skip, literal-`nget` edges, jinja regex; pins §4.5 (cycle recorded, no raise) and §4.6 (var/fn-ref edges silently dropped). Has its own `fixtures/`. Distinct pure-logic target. |
| `unit_contracts` | **keep** | All `to_dict`/`from_dict` round-trips (steps, plan, subflow*, retry, payloads) + §4.1 `output_keys` absent/null/`[]` asymmetry pin + `GroupConfig.resolved()` + naming collision §5. Merged from 5 tiny scenarios; still one coherent "contracts" theme. |
| `unit_executor_dispatch` | **keep** | Public executor `start()` payloads/orchestrator selection, plan type rejection, caller-supplied parent ID → deterministic child IDs, retry-policy threading, and a minimal custom `DurableFlowExecutor` through `run_durable_flow`. Covers the extension seam without an Azure host. |
| `unit_retry_scheduling` | **keep** | Drives the single-node and sequence retry generators with fake Durable contexts: exact exponential delay math, jitter Activity vs no-jitter path, durable timers, and preservation of the final underlying exception. Deterministic replacement for unreliable Azurite wall-clock timing. |
| `unit_subflow_scheduling` | **keep** | `schedule_step` input filtering + the §4.2/§4.3 pin (no `retry_policy`, no `instance_id` threaded) via a stub context, `extract_subflow_groups` + `merge`, and deterministic `max_concurrent=2` group batching (2-then-1) with ordering/input-threading assertions. The single most important defect characterization; do not fold away. |
| `unit_event_client_url` | **keep** | `DurableHttpEventClient.raise_event` URL construction (bare/trailing-slash host, `?code` key, localhost key-skip, both `RuntimeError`s) via stdlib `unittest.mock`. Distinct HTTP-mocking machinery — kept separate for clarity. |
| `unit_registration` | **keep** | Pins the dedicated test-host health identity contract; verifies `register_durable_support` registers the exact 10-function set (fake `Blueprint`, no double-register) and honors a custom `DurableEventClient`; covers telemetry off and enabled virtual-span propagation plus jitter activity bounds. "Host-side helpers" bundle. |

## Live — need Azurite + `func start`; gated on plugin + host probe

| Scenario | Verdict | What it covers / why |
|---|---|---|
| `durable_dag` | **keep** | `FLOW_ORCHESTRATOR` node→node signalling: linear chain + fan-out/fan-in + a real multi-second durable wait (asserts elapsed ≥ 3s). Merged from `durable_single_flow`+`fan_in_fan_out`+`long_running_dependency`. |
| `durable_dag_edges` | **keep** | High-risk single-DAG behavior: caller-supplied child instance IDs, node failure with no policy, non-literal `nget` portability failure, and the cycle-hang characterization. The cycle poll is self-bounded and both the parent and parked node children are always terminated. A separate live diamond is unnecessary because `durable_dag`'s source→3 branches→fan-in is stricter, while `unit_build_dag` pins the exact diamond. |
| `parallel_basic` | **keep** | `PARALLEL_ORCHESTRATOR`: input isolation (no step sees another's output) + result shape + mixed DIRECT/DURABLE. Merged `parallel_mixed_mode` in. |
| `parallel_retry` | **keep** | Retry-only-the-failed-step (recovers, with attempt counters proving healthy siblings stay at attempt 1) + all-or-nothing exhaustion (whole orchestration fails). Merged from 2. Requires the host's native-retry-disabled config. |
| `sequence_chain_depth` | **keep** (first cut candidate) | 4-deep sequence chain reusing one flow dir with distinct `name=`/`inputs`, all DIRECT. Distinct from key-filtering (tests depth/threading). If a further reduction is ever needed, this is the first to fold into `sequence_key_filtering`. |
| `sequence_key_filtering` | **keep** | `input_keys` allow-list filtering + `output_keys` forwarding + default-`[]`, DIRECT→DURABLE propagation, and same-flow unnamed result collision. Merged from `sequence_argument_passing`+`sequence_input_keys`+`sequence_output_keys`; reuses `_flows/echo`+`probe`. |
| `sequence_retry` | **keep** | The sequence-specific retry loop: only the current failing step retries, exhaustion fails the plan, and the §4.3 high-severity characterization that plan-level retry re-executes completed side effects in both DIRECT and DURABLE modes (`effect_count == 2`). |
| `subflow_dispatch` | **keep** | `SUBFLOWS_ORCHESTRATOR` flat dispatch via BOTH the sequence and parallel code paths + flat ≡ single `__default__` group equivalence + same-name collision. Merged from 4. |
| `subflow_groups` | **keep** | Host-level staged-group result shape + `skip_group_output` + `default_group_config` inherit/override. Exact batching/order is asserted offline in `unit_subflow_scheduling`; Azurite is not used as a wall-clock oracle (§4.9). Merged from 2. |
| `subflow_nested` | **keep** | 2-level recursive subflow dispatch (a subflow's node returns another `DurableSubflowOutput`). Distinct recursion behavior; not covered elsewhere. |
| `subflow_failure` | **keep** | §4.2 characterization pin: a subflow failing once under `attempts=3` is still fatal — the `DurableRetryPolicy` never reaches subflow steps. Fixing the package flips this to Completed and breaks the test deliberately. Keep as its own named scenario. |

## Deliberately deferred integration-only checks

- A real OpenTelemetry SDK/exporter connected across host process boundaries. Offline tests
  cover telemetry gating, parent extraction, attributes, child injection, and no-op behavior;
  exporter correctness belongs to the host application's telemetry integration.
- Wall-clock retry/jitter variance under Azurite. Azurite is known to fire Durable timers
  early, so the suite asserts exact scheduling deterministically in `unit_retry_scheduling`
  instead of adding a flaky elapsed-time test.
- A live crafted child-ID collision and parallel "first failure by index." The naming
  collision is pinned offline; creating conflicting task-hub instances adds cleanup risk,
  while the index-order rule is low-value error-selection behavior rather than execution
  correctness.
