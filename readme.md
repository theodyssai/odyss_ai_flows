# Odyss AI Flows

Opinionated, async-first, code-first orchestration for AI and LLM systems.

## Table of Contents

- [AI-first Documentation](#ai-first-documentation)
- [What Is Odyss AI Flows?](#what-is-odyss-ai-flows)
- [Quick Start](#quick-start)
- [Project Status](#project-status)
- [Packages & Plugins](#packages--plugins)
- [Coming Soon — October 2026](#coming-soon--october-2026)
- [Documentation](#documentation)
- [Examples](#examples)
- [Developing with a Coding Agent](#developing-with-a-coding-agent)
- [OpenRouter & Free Model Access](#openrouter--free-model-access)
- [API Keys & Secret Handling](#api-keys--secret-handling)
- [Philosophy & Execution Model](#philosophy--execution-model)
- [Testing](#testing)
- [License, Warranty & Responsibility](#license-warranty--responsibility)
- [Contributing](#contributing)

## AI-first Documentation

Read the sections you need, or give this README to an LLM and ask it to explain the project for your background and use case. That is an intended way to use the documentation. Ask about setup, architecture, comparisons, design choices, or project fit.

> Explain Odyss AI Flows for a Python developer building a document review workflow. What fits, what needs care, and how do I start?

## What Is Odyss AI Flows?

Odyss AI Flows composes Python logic and model calls into flows with extremely low boilerplate. It is not a declarative agent framework: it gives you lower-level control over data flow, execution, and how model reasoning connects to application code. Declarative agent support can be built on top through extensions.

Python nodes hold application logic; Jinja nodes hold prompts. Async execution and explicit dependencies connect them. Provider plugins supply model execution, including structured outputs, actions, streaming, and multimodal requests where the selected model supports them. Execution extensions support more demanding workloads, including durable execution through Azure Durable Functions.

The same framework can host deterministic flows, guided AI decisions, branching and parallel execution, or dynamic and agentic behavior. You choose the structure and keep it inspectable, without having to adopt a universal “agent” abstraction or hidden agent runtime.

## Quick Start

The current pre-PyPI setup uses editable installations from absolute paths in a local clone. This is the development distribution path, not the intended permanent installation experience.

You need Git and Python. We have tested **3.11.7** and **3.14.7**; versions between them are expected to work, so you do not need to install 3.11.7 specifically. You will also need an OpenRouter key and a suitable text model to run the starter. If API access is new to you or cost is a concern, start with [OpenRouter & Free Model Access](#openrouter--free-model-access). No Azure infrastructure is needed.

The walkthrough below uses Windows PowerShell. Work through it from the directory where you keep projects; each step explains what it creates or changes. No coding agent is required.

**1. Download the framework.** This creates an `odyss_ai_flows` repository folder:

```powershell
git clone https://github.com/theodyssai/odyss_ai_flows.git
```

Save its absolute path in a shell variable so later installation commands can find the packages even after you change directories:

```powershell
$OdyssRepo = (Resolve-Path '.\odyss_ai_flows').Path
```

**2. Create your application folder.** Keep it next to the framework checkout. The first command creates it; the second makes it your working directory:

```powershell
New-Item -ItemType Directory -Path '.\my-odyss-app'
Set-Location '.\my-odyss-app'
```

**3. Create a virtual environment.** Replace the example path with the Python executable you want to use. This creates `.venv` inside your application:

```powershell
& 'C:\Path\To\Python\python.exe' -m venv .venv
```

The following commands call this environment's executables explicitly, so shell activation is unnecessary. If using VS Code, review the repository and application files, trust the workspace if appropriate, and select the application's `.venv` interpreter.

**4. Install core and the OpenRouter plugin.** Core supplies the framework and `odyss` command; the plugin supplies the starter's model handler:

```powershell
& '.\.venv\Scripts\python.exe' -m pip install -e "$OdyssRepo\odyss_ai_flows_core"
& '.\.venv\Scripts\python.exe' -m pip install -e "$OdyssRepo\plugins\odyss_ai_flows_openrouter"
```

`-e` makes these editable installations: they import from your clone, so source changes take effect in this environment. Keep the clone at its current location while using it.

**5. Generate the starter.** Run `odyss init` in your application folder:

```powershell
& '.\.venv\Scripts\odyss.exe' init
```

It creates the following files and refuses to overwrite existing starter paths:

| File | What it is for |
| --- | --- |
| `main.py` | Loads local settings, supplies runtime inputs, runs the flow, and prints the result. |
| `.env.example` | A template for your local connection settings. |
| `global_config.json` | A named connection profile with environment references. Global config is optional; profiles can also live in scoped config files. |
| `flow/config.json` | Selects the connection and explicitly selects the OpenRouter pipeline. |
| `flow/subject.py`, `flow/ideas.jinja2`, `flow/final.jinja2` | The three example nodes. |
| `AGENTS.md` | Application-authoring instructions for a coding agent, also useful to read yourself. |
| `.gitignore` | Excludes `.env.local`, `.venv`, and Python-generated files. |

**6. Add your connection settings.** Copy the template to the local file that `main.py` will load:

```powershell
Copy-Item -LiteralPath '.env.example' -Destination '.env.local'
```

Open `.env.local` in your editor and replace the key and model placeholders:

```dotenv
OPENROUTER_API_KEY=your-api-key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=your-provider/your-model
```

These are placeholders; choose an actual model before running. The base URL ends at `/api/v1`, not `/chat/completions`.

**7. Inspect and run the example.** Open `main.py` to see the topic, the flow call, and the comments about alternatives to storing an API key in `.env.local`. Then run it from the application root:

```powershell
& '.\.venv\Scripts\python.exe' main.py
```

The starter runs one Python node and two LLM nodes: normalize a topic, generate three ideas, and produce a decision brief. Successful execution prints `Final result:` followed by the brief. Text varies by model; provider charges and limits depend on your selection.

Continue by changing the topic in `main.py` or extending `flow/`. If working with a coding agent, have it read the generated `AGENTS.md` first.

On macOS/Linux, use the same sequence with your installed Python executable, `.venv/bin/python` and `.venv/bin/odyss`; use `mkdir`, `cd`, and `cp` for the folder and copy steps. Supply absolute paths to the two package directories when installing. The isolated end-to-end checks described here were performed on Windows.

## Project Status

Development is very active. Internal maturity and public release stability are separate: core behavior is mature and internally proven, while the public release process, documentation, and API commitments are still being established.

🟢 mature / working · 🟡 advanced but evolving · 🟠 experimental / early · 🔴 known major limitation

| Area | Status | What this means |
| --- | --- | --- |
| Core features and stability | 🟢 Mature, internally proven | Not yet an official stable public release. |
| `odyss init` and generated example | 🟢 Tested and working | Covers a limited subset of framework features. |
| Documentation | 🟠 Being rebuilt | Extensive and useful as reference; largely AI-generated, with parts behind current implementation. |
| Examples | 🟠 Early collection | One canonical starter example; more planned. |
| Test harness | 🟢 Working | Dedicated filesystem, async, integration, and use-scenario testing. |
| Public API stability | 🟡 Evolving | Compatibility is not guaranteed; APIs and extension surfaces may change. |

Package metadata requires Python `>=3.11`. We have tested **3.11.7** and **3.14.7**, and expect versions between them to work. These are the tested endpoints of the range, not a claim that every intermediate version or deployment environment has been tested.

## Packages & Plugins

Install core plus the plugins your application needs. Versions below are the current repository versions, not a claim of PyPI availability. Maturity labels describe implementation experience, not a stability guarantee inferred from the version number.

| Package | Version | Maturity / status | Purpose and notes |
| --- | --- | --- | --- |
| [`odyss_ai_flows`](odyss_ai_flows_core/) | `0.4.1` | 🟢 Mature, internally proven | Flow runtime, node composition, configuration, extensibility, and `odyss init`; public release process underway. |
| [`odyss_ai_flows_openrouter`](plugins/odyss_ai_flows_openrouter/) | `0.1.1` | 🟡 Very advanced, almost production-ready | Default starter integration; OpenRouter-oriented, with configurable OpenAI-compatible endpoints. |
| [`odyss_ai_flows_artifacts`](plugins/odyss_ai_flows_artifacts/) | `0.1.1` | 🟡 Advanced, internally proven | Artifact storage and adapters; not yet production-ready. |
| [`odyss_ai_flows_azure`](plugins/odyss_ai_flows_azure/) | `0.1.1` | 🟡 Advanced, internally proven | Azure OpenAI integration with an Azure identity focus and API-key support. Prefer the OpenRouter-oriented integration for general projects. |
| [`odyss_ai_flows_cache`](plugins/odyss_ai_flows_cache/) | `0.1.1` | 🟠 Experimental | Caching integration. |
| [`odyss_ai_flows_durable`](plugins/odyss_ai_flows_durable/) | `0.1.1` | 🟡 Advanced, internally proven | Azure Durable Functions execution; known issues remain. |
| [`odyss_ai_flows_token_limiter`](plugins/odyss_ai_flows_token_limiter/) | `0.1.1` | 🟠 Experimental, core behavior tested | Redis-backed token accounting and threshold middleware; enforcement limitations remain. |

The OpenRouter handler has also been exercised against Azure OpenAI Foundry with API-key authentication. Endpoint, model, and optional-parameter compatibility still matter; an OpenAI-compatible URL alone does not establish support for every feature.

The token limiter has tests for accounting, blocking, soft limits, and real model usage, using simulated Redis. Its preflight check currently reads stored usage without applying elapsed-time decay, and accounting occurs after calls rather than reserving capacity before them. Treat it as accounting and threshold enforcement under development, not a strict concurrent token-budget guarantee.

## Coming Soon — October 2026

Planned work for October, without fixed delivery dates within the month:

- Guides for creating major plugin types and coding-agent instructions for plugin authors.
- Full plugin/extensibility documentation and rebuilt framework documentation.
- Contribution guidelines and a framework-contributor root `AGENTS.md`.
- More canonical examples.

## Documentation

The [documentation tree](docs/) is extensive. Much of it was AI-generated from implementation during earlier development iterations, and parts lag behind current APIs. It is useful as technical reference, but it does not represent the intended final documentation quality. It is actively being rebuilt.

For onboarding, prefer this README, `odyss init`, its generated `AGENTS.md`, and the canonical starter. Use older documentation to investigate a specific topic, with attention to possible API drift.

To preview the existing MkDocs documentation, run from the repository root in a development environment:

```shell
python -m pip install mkdocs
python -m mkdocs serve
```

Open the local address reported by MkDocs, normally `http://127.0.0.1:8000`.

## Examples

There is currently one canonical example: the application generated by `odyss init`. Its [source templates](odyss_ai_flows_core/odyss_ai_flows/_starter_templates/) are shipped with core; a broader example library is planned.

The starter's dependency chain is:

```text
subject.py → ideas.jinja2 → final.jinja2
     └───────────────────────↑
```

`subject` reads the runtime topic, `ideas` proposes candidates, and `final` uses both to write a brief. This demonstrates Python/Jinja composition, explicit dependencies, named connections, and scoped configuration. It is not a demonstration of the full framework feature set.

## Developing with a Coding Agent

A coding agent can read and edit your project files and run commands as you develop. Odyss gives it a starting point: `odyss init` creates **`AGENTS.md` in your application root, next to `main.py`**. This file explains how to write nodes, connect flows, use configuration, and run the application.

Open that application folder in your coding harness and ask the agent to read `AGENTS.md` before building anything. This gives it concrete framework conventions without requiring you to teach them in every prompt. You describe the application you want, review the changes, and supply your own environment values.

> Read AGENTS.md and the starter files. Help me build [my use case] as a separate flow. Explain the proposed structure and model calls before editing. I will provide the API key; do not display it.

This workflow has been tested from a fresh project through real provider-backed execution in an isolated Codex sandbox. Other coding harnesses may use the guidance too, but have not all been validated. Giving this README to an LLM helps you understand the project; the generated `AGENTS.md` helps an agent work inside your application.

## OpenRouter & Free Model Access

If you are curious about Odyss but do not yet have an API key, are unsure which model to try, or want to keep your first experiment inexpensive, this is the starting path for you. The OpenRouter starter lets you try a real model-backed flow without setting up Azure or choosing a long-term provider architecture first.

Create an [OpenRouter account and API key](https://openrouter.ai/docs/quickstart), then browse the [model catalog](https://openrouter.ai/models) for a suitable text model. Some models have [free variants](https://openrouter.ai/docs/guides/routing/model-variants/free), which can make a small first experiment accessible without paying for model tokens. Copy the exact identifier of your chosen model into `OPENROUTER_MODEL`.

Free access is offered by the provider, not guaranteed by Odyss. Availability, quotas, pricing, and supported features can change; check the current listing before running. The starter makes two model calls and does not automatically select a free model. If you choose a paid model, normal provider charges apply.

Ordinary text generation is enough for the starter. You can explore structured outputs, actions, or multimodal inputs later with a model that supports them.

## API Keys & Secret Handling

Secret loading belongs to the application. Core deliberately does not automatically load `.env` files. The generated `main.py` loads `.env.local` before importing the framework and reports a clear error if you have not created it from `.env.example`. Existing process environment variables take precedence over dotenv values.

Choose the approach that fits the application:

1. **Environment / `.env.local`:** the simplest local setup. The starter excludes `.env.local` from Git; keep real keys out of source, logs, and shared prompts.
2. **Application-controlled bootstrap:** use the documented hook in `main.py` to fetch a secret through your preferred mechanism and inject it into the Python process environment before framework initialization. Adapt the local-file check/loading if your application no longer uses `.env.local`.
3. **Reusable extension:** implement a custom Odyss config/secret plugin when secret resolution should be shared across applications.

The generated entry point already explains local-file handling and the application bootstrap hook. A virtual environment isolates Python dependencies; it is not a secret store.

## Philosophy & Execution Model

Odyss starts with data flow: a flexible graph of nodes that consume and produce values. An LLM call is one kind of work in that graph. Ordinary Python transformations, validation, retrieval, and control logic belong there too; a flow can be useful without making any model calls.

The design favors a compact core, few dependencies, and no mandatory provider extension. Focused modules keep responsibilities readable and allow individual parts to evolve independently. Low boilerplate keeps attention on the work itself and makes rapid prototypes easier to change as requirements become clearer.

AI is an execution component, not the orchestration platform. Reasoning, deciding which action to take, formatting a structured request, and executing code have different responsibilities. You can keep them in distinct nodes, give each its own prompt or model, and validate the data crossing those boundaries. This lets you tune a reasoning step without rewriting tool execution and see which stage failed. The separation creates places to enforce controls; it does not make model output automatically correct.

Explicit inputs and outputs also give an application somewhere to carry source references, findings, and decision records through successive steps. That makes data lineage and review possible when the application records them. Model explanations remain outputs to evaluate, rather than proof of how a conclusion was reached.

In the default async execution model, nodes start independently and request dependencies with `nget()`. Python awaits those values explicitly; Jinja nodes use the same dependency operation through async template rendering. Dependencies live where values are consumed, without requiring a separately maintained central graph.

```python
from odyss_ai_flows import *

@node
async def recommendation():
    evidence = await nget("evidence")
    return {"approved": evidence["score"] >= 0.8}
```

This illustrative node belongs in `recommendation.py` alongside a node named `evidence`. Deterministic decisions like this can sit beside prompts and model-selected actions. Python can express branches, bounded loops, parallel work, and calls to other flows. You choose how much behavior is fixed and where a model has discretion, while retaining explicit control over iteration, state, and execution.

A directory selected by `run_flow()` includes supported node files recursively. Subfolders organize nodes and narrow configuration scope; they do not create separate flow boundaries. Keep separately callable flows outside a parent directory that you also execute as a flow. Branches should deliberately select the work to run, rather than rely on unused files being ignored.

Provider execution uses composed handler pipelines; configuration selects connections and behavior. This separation lets model integrations and execution strategies evolve without forcing application logic into a provider-specific orchestration language. Async execution and the durable executor provide paths toward scalable execution, with deployment and operational choices remaining explicit.

Inspectability means being able to locate prompts, code, dependencies, configuration, and handler choices. Composability means combining ordinary logic and model work without erasing their differences. Operational control means keeping the application's decisions about execution and oversight in view—even when its reasoning is dynamic.

## Testing

Odyss uses a dedicated [custom test harness](tests/) because it is a flow/DSL engine: correctness spans filesystem scenarios, async execution, configuration scope, integration behavior, and complete use cases. Live provider tests complement local checks where remote behavior matters.

The harness is installable as `odyss_ai_flows_tests` and exposes `odyss-ai-flows-test`. The repository's [PowerShell runner](Test-OdyssPython.ps1) creates isolated package environments, offers interactive test selection, and supports optional cleanup. Configured integration runs use the runner's sibling `.env.local`; live durable scenarios need Azure Functions and Azurite. The script manages their local test processes and documents its options in its built-in help.

Passes, failures, and skips are distinct outcomes. A skipped integration scenario is not evidence that its behavior works. Known durable issues remain; Python compatibility checks do not imply an entirely green integration suite.

## License, Warranty & Responsibility

Odyss AI Flows is licensed under Apache License 2.0 and is provided **“AS IS”**, without warranties or conditions of any kind, subject to the license's terms and applicable law. See [LICENSE](LICENSE) for the actual legal terms and [NOTICE](NOTICE) for attribution and notices.

You are responsible for evaluating suitability for your use case, environment, security requirements, and applicable law. The framework orchestrates external models, tools, services, and user-defined code; this project does not guarantee their outputs or behavior. Depending on the application, appropriate validation, permissions, monitoring, and human oversight may be required.

## Contributing

Contribution guidelines are not finalized. The planned October work includes contributor guidance, plugin-authoring documentation, and a root `AGENTS.md` for framework development. The application `AGENTS.md` generated by `odyss init` is intended for building applications, not for defining the framework's contribution process.
