"""Validation of provisional usage events followed by converged variable facts."""
from __future__ import annotations

import grpc
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit._generated.analysis.v1.variable_flow_pb2 import VariableFlowEvent


class VariableFlowState:
    def __init__(self) -> None:
        self.started = self.completed = self.facts_started = False
        self.usages = self.facts = self.findings = 0

    def require(self, condition: bool) -> None:
        if not condition:
            raise AnalysisError(grpc.StatusCode.DATA_LOSS, "invalid variable flow stream ordering or counts")

    def consume(self, event: VariableFlowEvent) -> None:
        self.require(not self.completed)
        kind = event.WhichOneof("event")
        if kind == "started":
            self.require(not self.started and event.started.snapshot_generation > 0 and
                         event.started.declaration_id > 0 and event.started.HasField("declaration"))
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
            self.facts += 1
        elif kind == "finding":
            self.require(1 <= event.finding.kind <= 4 and event.finding.usage_id <= self.usages)
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
