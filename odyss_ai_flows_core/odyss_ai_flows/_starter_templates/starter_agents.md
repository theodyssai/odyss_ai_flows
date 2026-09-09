# Building with Odyss AI Flows

This repository is an application built with Odyss AI Flows. Work on the application here; do not treat it as a checkout of the framework itself.

## Project structure

- `main.py` is the executable application entry point.
- `flow/` is the starter flow. Each supported file in this directory is a node.
- `global_config.json` contains project-wide configuration and reusable connection profiles.
- `flow/config.json` contains configuration scoped to this flow.
- `.env.local` is local configuration and must not be committed. Start from `.env.example`.

Run commands from the project root. Configuration discovery and relative flow paths depend on the current working directory.

## Core concepts

A flow is either one node file or a directory of nodes. Python nodes use the `@node` decorator; `.jinja2` files are LLM nodes handled by the installed provider plugin. Filesystem structure defines flow and configuration scope.

Nodes start independently. Express dependencies where their values are needed:

- In Python nodes, use `await nget("node_name")`.
- In Jinja nodes, use `{{ nget("node_name") }}` without `await`; the framework awaits it.
- Use `iget()` for values passed to `run_flow(..., inputs={...})`.
- Use `await cget()` in Python or `{{ cget(...) }}` in Jinja for scoped configuration.

Keep node names unique within a flow. The node name comes from the filename and should match the decorated Python function name. Avoid hidden module-level side effects; flow work belongs inside nodes.

## Creating and composing flows

Add a Python node as `flow/example.py`:

```python
from odyss_ai_flows import *

@node
async def example():
    upstream = await nget("subject")
    return {"value": upstream}
```

Add an LLM node as `flow/example.jinja2`. It can reference upstream results with `nget()`. A Python node may compose another flow with `await run_flow("path/to/flow", inputs={...})`.

Do not create a separate central dependency graph. Dependencies expressed through `nget()` are the orchestration graph.

## Configuration

Configuration is hierarchical and merges from broad to specific:

```text
global_config.json
  -> flow/config.json
  -> nested_folder/config.json
  -> node_name.config.json
```

Dictionaries merge across scopes; scalar values at narrower scopes replace broader values. Use dotted keys with `cget()`. Keep infrastructure settings in configuration rather than node code.

The starter defines the reusable `azure_openai` connection globally and selects it with `oai_connection_name` in `flow/config.json`. A nested folder or node config can select a different named connection without changing flow code.

Semantic configuration values use Jinja-style providers such as `ENV(...)`, `CONFIG(...)`, `VAULT(...)`, `REF(...)`, and `SECRET(...)`. Do not combine `REF()` with other text or providers in the same value. Never print or serialize unwrapped secrets.

## Azure OpenAI

The `.jinja2` nodes use the Azure handler supplied by `odyss_ai_flows_azure`. The connection requires:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_DEPLOYMENT`

This starter deliberately omits `api_key`. The Azure plugin therefore uses `DefaultAzureCredential`, which can use an active `az login`, managed identity, workload identity, or another supported Azure identity. The identity must have permission to invoke the deployment.

Do not add an API key merely to work around an identity or RBAC problem. Add `api_key` to the selected connection only when API-key authentication is an intentional deployment decision.

## Running the starter

Install the core package and Azure plugin in the active environment, authenticate, configure, and run:

```powershell
Copy-Item .env.example .env.local
az login
python main.py
```

Fill the three Azure values before running. Successful execution prints the result of the final node.

## Extending safely

- Add one node at a time and keep its inputs, dependencies, and returned value obvious.
- Inside ordinary node files, prefer `from odyss_ai_flows import *`. The public interface intentionally exports only the small node-authoring surface (`cget`, `iget`, `inspect_flow`, `logger`, `model`, `node`, `nget`, `run_flow`, `FlowResult`, `SensitiveValue`, `unwrap`, `Action`, and `ExecutorMode`), keeping node boilerplate and token usage low.
- Continue to use explicit imports for plugin APIs, advanced integrations, and non-public framework internals so their origins and coupling remain visible.
- Keep prompts in `.jinja2` nodes and deterministic transformation/control logic in Python nodes.
- Use `nget()` only for real dependencies; accidental dependency cycles fail execution.
- Put shared settings in `global_config.json`, flow-specific settings in `config.json`, and exceptional overrides in `node_name.config.json`.
- Pass runtime data through `inputs`/`iget()` rather than storing mutable global state.
- Preserve async behavior: await `nget()`, `cget()`, and `run_flow()` in Python.
- Run from the project root and inspect the complete flow result when debugging before assuming an Azure failure.
