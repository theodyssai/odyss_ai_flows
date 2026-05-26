from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import sys
import traceback

from pathlib import Path


# ---------------------------------------------------------
# Logger setup
# ---------------------------------------------------------

from odyss_ai_flows.core.utils.logger import (
    logger,
)

from tests.tests_runtime.global_config import (
    cleanup_global_config,
    prepare_global_config,
)

from tests.tests_runtime.scenario_protocol import (
    ScenarioRuntimeDefinition,
)

from tests.tests_runtime.scenario_runtime import (
    execute_scenario,
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _load_module_from_path(
    path: Path,
):

    spec = importlib.util.spec_from_file_location(
        "scenario_module",
        str(path),
    )

    if spec is None or spec.loader is None:

        raise RuntimeError(
            f"Could not load scenario module: "
            f"{path}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(module)

    return module


def _attach_file_logger(
    log_path: Path,
) -> logging.Handler:

    handler = logging.FileHandler(
        log_path,
        encoding="utf-8",
    )

    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(message)s"
    )

    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return handler


def _write_result(
    result_path: Path,
    payload: dict,
) -> None:

    result_path.write_text(
        json.dumps(
            payload,
            indent=4,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------
# Async execution
# ---------------------------------------------------------

async def _run_scenario(
    scenario_file: Path,
):

    generated_global = (
        prepare_global_config(
            scenario_file.parent
        )
    )

    try:

        module = _load_module_from_path(
            scenario_file
        )

        run_scenario = getattr(
            module,
            "run_scenario",
            None,
        )

        if run_scenario is not None:

            if not callable(run_scenario):

                raise TypeError(
                    f"'run_scenario' in "
                    f"'{scenario_file}' "
                    f"is not callable"
                )

            result = run_scenario()

            if asyncio.iscoroutine(result):

                return await result

            return result

        runtime = getattr(
            module,
            "runtime",
            None,
        )

        if runtime is None:

            raise RuntimeError(
                f"Scenario module "
                f"'{scenario_file}' "
                f"must define either "
                f"'run_scenario' or 'runtime'"
            )

        if not isinstance(
            runtime,
            ScenarioRuntimeDefinition,
        ):

            raise TypeError(
                f"'runtime' in "
                f"'{scenario_file}' "
                f"is not a "
                f"ScenarioRuntimeDefinition"
            )

        result = await execute_scenario(
            runtime
        )

        return result

    finally:

        cleanup_global_config(
            generated_global
        )


def _serialize_result_best_effort(
    result,
):

    if result is None:

        return None

    if hasattr(result, "to_dict"):

        try:

            return result.to_dict()

        except Exception:

            pass

    try:

        json.dumps(result)

        return result

    except Exception:

        return {
            "type": type(result).__name__,
            "repr": repr(result),
        }


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main() -> int:

    if len(sys.argv) != 4:

        print(
            "Usage: "
            "python -m tests.tests_runtime.scenario_entry "
            "<scenario.py> "
            "<result.json> "
            "<scenario.log>"
        )

        return 1

    scenario_file = Path(
        sys.argv[1]
    )

    result_path = Path(
        sys.argv[2]
    )

    log_path = Path(
        sys.argv[3]
    )

    handler = _attach_file_logger(
        log_path
    )

    try:

        result = asyncio.run(
            _run_scenario(
                scenario_file
            )
        )

        payload = {
            "success": True,

            "result": _serialize_result_best_effort(
                result
            ),

            "error": None,
        }

        _write_result(
            result_path,
            payload,
        )

        return 0

    except Exception as e:

        tb = traceback.format_exc()

        logger.error(tb)

        payload = {
            "success": False,

            "result": None,

            "error": {
                "type": type(e).__name__,

                "message": str(e),

                "traceback": tb,
            },
        }

        _write_result(
            result_path,
            payload,
        )

        return 1

    finally:

        logger.removeHandler(
            handler
        )

        handler.close()


# ---------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------

if __name__ == "__main__":
    raise SystemExit(main())