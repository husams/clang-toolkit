"""Validation of provisional usage events followed by converged variable facts."""
from __future__ import annotations

import re
import grpc
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit._generated.analysis.v1.variable_flow_pb2 import VariableFlowEvent, VariableValueRange


class VariableFlowState:
    def __init__(self, value_domain: int = 0) -> None:
        self.started = self.completed = self.facts_started = False
        self.usages = self.facts = self.findings = 0
        self.value_domain = value_domain

    def range_valid(self, value: VariableValueRange) -> bool:
        if value.kind == value.INTERVAL:
            decimal = r"(?:0|-?[1-9][0-9]{0,38})"
            if not all(re.fullmatch(decimal, x) for x in (value.lower, value.upper)):
                return False
            return -(1 << 127) <= int(value.lower) <= int(value.upper) < (1 << 127)
        return value.kind in (value.UNINITIALIZED, value.UNREACHABLE, value.UNKNOWN) and not value.lower and not value.upper

    def require(self, condition: bool) -> None:
        if not condition:
            raise AnalysisError(grpc.StatusCode.DATA_LOSS, "invalid variable flow stream ordering or counts")

    def consume(self, event: VariableFlowEvent) -> None:
        self.require(not self.completed)
        kind = event.WhichOneof("event")
        if kind == "started":
            self.require(not self.started and event.started.snapshot_generation > 0 and
                         event.started.declaration_id > 0 and event.started.HasField("declaration"))
            self.require(event.started.value_domain == self.value_domain and self.value_domain in (0, 1))
            self.started = True
            return
        self.require(self.started)
        if kind == "usage":
            self.require(not self.facts_started and not self.findings and event.usage.id == self.usages + 1 and
                         event.usage.provisional and 1 <= event.usage.kind <= 7)
            self.usages += 1
        elif kind == "fact":
            self.facts_started = True
            self.require(event.fact.usage_id == self.facts + 1 and self.facts < self.usages and
                         1 <= event.fact.initialization <= 4 and
                         all(0 <= value <= self.usages for value in event.fact.reaching_assignments))
            numeric = self.value_domain == 1
            self.require(event.fact.HasField("value_before") == numeric and
                         event.fact.HasField("value_after") == numeric)
            if numeric:
                self.require(self.range_valid(event.fact.value_before) and self.range_valid(event.fact.value_after))
            self.facts += 1
        elif kind == "finding":
            self.require(1 <= event.finding.kind <= 5 and event.finding.usage_id <= self.usages)
            self.findings += 1
        elif kind == "completed":
            value = event.completed
            self.require(value.usage_count == self.usages and value.fact_count == self.facts and
                         self.facts == self.usages and value.finding_count == self.findings)
            self.completed = True
        else:
            self.require(False)

    def finish(self) -> None:
        self.require(self.completed)
