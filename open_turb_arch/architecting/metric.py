"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Copyright: (c) 2020, Deutsches Zentrum fuer Luft- und Raumfahrt e.V.
Contact: jasper.bussemaker@dlr.de
"""

from typing import *
from open_turb_arch.architecting.choice import *
from open_turb_arch.architecting.opt_defs import *

__all__ = ['ArchitectingMetric', 'OutputMetric', 'ObjectiveDirection', 'Objective', 'ConstraintDirection',
           'Constraint', 'ArchitectingChoice', 'AnalysisProblem', 'OperatingMetricsMap', 'OperatingCondition',
           'DesignCondition', 'EvaluateCondition']


class ArchitectingMetric:
    """Base class that represents some output metrics that can be used for different roles in the optimization problem:
    as objective, as constraints, or as generic output metric."""

    def get_opt_objectives(self, choices: List[ArchitectingChoice]) -> List[Objective]:
        raise NotImplementedError

    def get_opt_constraints(self, choices: List[ArchitectingChoice]) -> List[Constraint]:
        raise NotImplementedError

    def get_opt_metrics(self, choices: List[ArchitectingChoice]) -> List[OutputMetric]:
        raise NotImplementedError

    def extract_met(self, analysis_problem: AnalysisProblem, result: OperatingMetricsMap) -> Sequence[float]:
        raise NotImplementedError

    def extract_obj(self, analysis_problem: AnalysisProblem, result: OperatingMetricsMap) -> Sequence[float]:
        return self.extract_met(analysis_problem, result)

    def extract_con(self, analysis_problem: AnalysisProblem, result: OperatingMetricsMap) -> Sequence[float]:
        return self.extract_met(analysis_problem, result)
