import platform
from itertools import groupby
from operator import attrgetter
from pathlib import Path
from typing import IO, Any, Optional, cast
from urllib.parse import urlparse

from opentelemetry import trace
from pydantic import BaseModel

from kai.analyzer import AnalyzerLSP
from kai.analyzer_types import Report
from kai.jsonrpc.models import JsonRpcError
from kai.logging.logging import TRACE, get_logger
from kai.reactive_codeplanner.task_manager.api import (
    RpcClientConfig,
    ValidationError,
    ValidationException,
    ValidationResult,
    ValidationStep,
)
from kai.reactive_codeplanner.task_runner.analyzer_lsp.api import (
    AnalyzerDependencyRuleViolation,
    AnalyzerRuleViolation,
)

logger = get_logger(__name__)
tracer = trace.get_tracer("analyzer_validator")


def log_stderr(stderr: IO[bytes]) -> None:
    for line in iter(stderr.readline, b""):
        logger.info("analyzer_lsp rpc: " + line.decode("utf-8"))


class AnalyzerLSPStep(ValidationStep):
    included_paths: list[Path]
    excluded_paths: list[Path]

    def __init__(self, config: RpcClientConfig, analyzer: AnalyzerLSP) -> None:
        self.analyzerLSP = analyzer
        self.included_paths = config.included_paths or []
        self.excluded_paths = config.excluded_paths or []
        super().__init__(config)

    @tracer.start_as_current_span("analyzer_run_validation")
    async def run(self, scoped_paths: Optional[list[Path]] = None) -> ValidationResult:
        logger.debug("Running analyzer-lsp")

        # TODO(djzager): should these be arguments?
        analyzer_output = await self.analyzerLSP.run_analyzer_lsp(
            scoped_paths=scoped_paths,
        )

        # TODO: Possibly add messages to the results
        ValidationResult(
            passed=False,
            errors=[
                ValidationError(
                    file="", line=-1, column=-1, message="Analyzer LSP failed"
                )
            ],
        )
        if analyzer_output is None:
            raise ValidationException(message="Analyzer LSP failed to return a result")
        elif isinstance(analyzer_output, JsonRpcError):
            raise ValidationException(
                message=f"Analyzer output is a JsonRpcError. Error: {analyzer_output}"
            )
        elif analyzer_output.result is None:
            raise ValidationException(message="Analyzer lsp's output is None")
        elif isinstance(analyzer_output.result, BaseModel):
            logger.log(TRACE, "analyzer_output.result is a BaseModel, dumping it")
            logger.log(TRACE, analyzer_output.result)
            analyzer_output.result = analyzer_output.result.model_dump()
        else:
            logger.log(TRACE, "analyzer_output.result is not a BaseModel")
            logger.log(TRACE, analyzer_output.result)

        errors = self.__parse_analyzer_lsp_output(analyzer_output.result)
        return ValidationResult(
            passed=not errors, errors=cast(list[ValidationError], errors)
        )

    def __parse_analyzer_lsp_output(
        self, analyzer_output: dict[str, Any]
    ) -> list[AnalyzerRuleViolation]:
        logger.debug("Parsing analyzer-lsp output")

        rulesets = analyzer_output.get("Rulesets")

        if not rulesets or not isinstance(rulesets, list):
            logger.info("parsed zero results from validator")
            return []

        r = Report.load_report_from_object(rulesets, "analysis_run_task_runner")

        validation_errors: list[AnalyzerRuleViolation] = []
        rulesetNamesSorted: list[str] = list(r.rulesets.keys())
        rulesetNamesSorted.sort()
        logger.debug("getting rulesetNames sorted %s", rulesetNamesSorted)
        for key in rulesetNamesSorted:
            violationsSortedKeys: list[str] = list(r.rulesets[key].violations.keys())
            violationsSortedKeys.sort()
            logger.debug("getting sorted violations %s", violationsSortedKeys)
            for violationKey in violationsSortedKeys:
                violation = r.rulesets[key].violations[violationKey]
                violation.incidents.sort()
                grouped_violations = [
                    list((g))
                    for _, g in groupby(violation.incidents, key=attrgetter("uri"))
                ]

                for incidents in grouped_violations:
                    violation.id = violationKey
                    uri_path = urlparse(incidents[0].uri).path
                    if platform.system() == "Windows":
                        uri_path = uri_path.removeprefix("/")
                    class_to_use = AnalyzerRuleViolation
                    if "pom.xml" in incidents[0].uri:
                        class_to_use = AnalyzerDependencyRuleViolation

                    validation_error = class_to_use(
                        file=str(Path(uri_path).absolute()),
                        violation=violation,
                        ruleset=r.rulesets[key],
                        line=0,
                        column=-1,
                        message="",
                        incidents=incidents,
                    )
                    logger.log(
                        TRACE,
                        "validation_error adding to list: %s -- incident_messages: %s",
                        validation_error,
                        validation_error.incident_message,
                    )
                    validation_errors.append(validation_error)

        return validation_errors
