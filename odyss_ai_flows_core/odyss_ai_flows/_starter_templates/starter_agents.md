# Building with Odyss AI Flows

This repository is an application built with Odyss AI Flows. Work on the application here; do not treat it as a checkout of the framework itself.

## Project structure

- `main.py` is the executable application entry point.
- `flow/` is the starter flow. Each supported file in this directory is a node.
- `global_config.json` contains project-wide configuration and reusable connection profiles.
- `flow/config.json` contains configuration scoped to this flow.
- `.env.local` is local configuration and must not be committed. Start from `.env.example`.

Run commands from the project root. Configuration discovery and relative flow paths depend on the current working directory.

## Authoring boundary

This file and the generated starter files are the authoritative guidance for application work in this repository.

- Do not inspect framework or plugin source code for implementation ideas, behavior, or conventions unless the user explicitly asks.
- Do not modify framework or plugin source repositories from this application project.
- If the guidance and starter files do not make required behavior clear, stop and ask the user rather than inferring it from framework internals.
- For prototype work, use only the installed public application API: `node`, `nget`, `iget`, `cget`, and `run_flow`.

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

## Flow directory semantics

A flow is an explicitly selected file or directory passed to `run_flow()`.

When a directory is run as a flow, all supported node files beneath that directory belong to the same flow. Subfolders do not create flow boundaries; use them only to organize nodes, label areas, or narrow configuration scope.

Never put a callable subflow directory inside a directory that will itself be run as a flow. Calling the child separately does not exclude its nodes when the parent directory is run.

For deliberate nested-flow composition, keep flow roots as siblings beneath an organizational directory that is never itself run:

```text
poc_decision/
  main_flow/                 # run_flow("poc_decision/main_flow")
    orchestrate.py
    memo.jinja2
    config.json
  subflows/
    score_candidate/         # run_flow("poc_decision/subflows/score_candidate")
      card.py
```

The orchestration node calls the project-relative subflow path:

```python
result = await run_flow(
    "poc_decision/subflows/score_candidate",
    inputs={"candidate": candidate},
)
```

Use `outputs.json` only when a caller needs an explicit public output contract. It is optional, should not be added by default, and must not appear more than once beneath an executed flow root.

## Configuration

Configuration is hierarchical and merges from broad to specific:

```text
global_config.json
  -> flow/config.json
  -> nested_folder/config.json
  -> node_name.config.json
```

Dictionaries merge across scopes; scalar values at narrower scopes replace broader values. Use dotted keys with `cget()`. Keep infrastructure settings in configuration rather than node code.

The starter defines the reusable `openrouter` connection globally and selects it with `oai_connection_name` in `flow/config.json`. It also names the fully qualified OpenRouter pipeline so installing another provider plugin does not silently change which handler runs. A nested folder or node config can select a different named connection and pipeline without changing flow code.

Semantic configuration values use Jinja-style providers such as `ENV(...)`, `CONFIG(...)`, `VAULT(...)`, `REF(...)`, and `SECRET(...)`. Do not combine `REF()` with other text or providers in the same value. Never print or serialize unwrapped secrets.

## OpenRouter

The `.jinja2` nodes use the handler supplied by `odyss_ai_flows_openrouter`. The connection requires:

- `OPENROUTER_API_KEY`
- `OPENROUTER_BASE_URL`
- `OPENROUTER_MODEL`

The default base URL is `https://openrouter.ai/api/v1`. It is the SDK base URL, not the complete `/chat/completions` request URL. Use an OpenRouter model identifier such as `provider/model`; availability and pricing depend on the selected model.

`main.py` deliberately loads `.env.local` before importing the framework. It also contains a documented bootstrap hook for projects that inject `OPENROUTER_API_KEY` from a secret manager or another secure source instead of storing the key in `.env.local`. Existing process environment variables win over dotenv values.

## Running the starter

Install the core package and OpenRouter plugin in the active environment, configure, and run:

```powershell
Copy-Item .env.example .env.local
python main.py
```

Set `OPENROUTER_API_KEY` and choose an `OPENROUTER_MODEL` before running. If `.env.local` was not created, `main.py` stops immediately with instructions instead of failing later during connection resolution. Successful execution prints the result of the final node.

## Prototype design standard

Before editing a prototype, state its proposed flow roots, every `run_flow()` target, its bounded iteration count, and the expected number of LLM calls.

For a low-cost, predictable proof of concept:

- Keep control flow, validation, scoring, selection, and loops in Python.
- Use a fixed small candidate set and a hard iteration bound.
- Make the decisive result deterministic before any LLM call.
- Use at most one short Jinja/OpenRouter call to explain or format that result.
- Give every runtime input a safe default and normalize it locally.
- Keep the existing starter flow intact and add a separate application entry point for each new proof of concept.

## Extending safely

- Add one node at a time and keep its inputs, dependencies, and returned value obvious.
- Inside ordinary node files, prefer `from odyss_ai_flows import *`. The public interface intentionally exports only a small node-authoring surface, keeping node boilerplate and token usage low. Follow the narrower API boundary above for prototype work.
- Continue to use explicit imports for plugin APIs, advanced integrations, and non-public framework internals so their origins and coupling remain visible.
- Keep prompts in `.jinja2` nodes and deterministic transformation/control logic in Python nodes.
- Use `nget()` only for real dependencies; accidental dependency cycles fail execution.
- Put shared settings in `global_config.json`, flow-specific settings in `config.json`, and exceptional overrides in `node_name.config.json`.
- Pass runtime data through `inputs`/`iget()` rather than storing mutable global state.
- Preserve async behavior: await `nget()`, `cget()`, and `run_flow()` in Python.
- Run from the project root and inspect the complete flow result when debugging before assuming an OpenRouter failure.
