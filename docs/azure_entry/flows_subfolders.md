# Flow Subfolders

Flows may contain any subfolder structure.

Subfolders are primarily organizational and allow flows to be structured in whatever way best fits the system being built.

Nodes can be grouped by:
- feature
- responsibility
- execution stage
- domain
- provider
- orchestration layer
- debugging utilities
- reusable components

or any other organizational approach preferred by the developer.

---

# Subfolders Do Not Define Execution Structure

Unlike some orchestration systems, folder hierarchy does not define execution hierarchy.

The framework does not treat subfolders as:
- nested flows
- execution stages
- isolated scopes
- sequential layers

Execution relationships are determined entirely through:
- `nget()`
- runtime orchestration
- node interactions

not folder structure.

This means nodes can freely depend on nodes located anywhere within the flow regardless of directory depth.

---

# Example Structure

Example flow structure:

```text
global_config.json

flow_root/
├── config.json
├── subfolder_1/
│   ├── config.json
│   ├── node_1.jinja2
│   └── node_2.py
│
├── subfolder_2/
│   ├── node_3.jinja2
│   └── sub_subfolder/
│       ├── config.json
│       └── node_4.py
```

In this example:
- folders are used purely for organization
- nodes remain part of the same flow
- execution behavior is unaffected by nesting depth

---

# Configuration Scope

Although folders do not affect orchestration structure, they do affect configuration scoping.

`config.json` files become increasingly specific as they get closer to a node.

This allows different parts of a flow to have:
- different model settings
- different execution parameters
- different providers
- different middleware behavior
- different runtime configuration

while still remaining part of the same flow.

Example:

```text
flow_root/config.json
```

may define general flow defaults, while:

```text
flow_root/subfolder_2/sub_subfolder/config.json
```

may override settings specifically for nodes in that deeper folder.

---

# Node Names Remain Global Within a Flow

Even when nodes are located in deeply nested folders, node identities remain flow-global.

Example:

```python
await nget("node_4")
```

or:

```jinja2
{{ nget("node_4") }}
```

works regardless of where the node is physically located inside the flow folder structure.

This keeps orchestration simple while allowing filesystem organization to remain flexible.

---

# Why This Design Exists

The framework intentionally separates:
- organizational structure
- execution structure

This avoids coupling orchestration logic to filesystem layout.

As flows grow larger, developers can freely reorganize folders without rewriting execution relationships.

This allows:
- large flow refactors
- clearer project organization
- modular grouping
- cleaner maintenance
- scalable repository structures

without changing runtime orchestration behavior.

---

# Practical Usage

Small flows often remain completely flat:

```text
simple_flow/
├── prompt.jinja2
├── summary.jinja2
└── cleanup.py
```

Larger systems may use extensive folder organization:

```text
large_flow/
├── ingestion/
├── preprocessing/
├── enrichment/
├── orchestration/
├── reporting/
├── monitoring/
└── debugging/
```

Both approaches behave identically from the executor's perspective.

The folder structure exists for developer organization and configuration specificity rather than orchestration semantics.