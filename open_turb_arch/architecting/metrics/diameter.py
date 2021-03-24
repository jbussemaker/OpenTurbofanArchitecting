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
from dataclasses import dataclass
from open_turb_arch.architecting.metric import *
from open_turb_arch.evaluation.analysis.disciplines import *
from open_turb_arch.evaluation.architecture import *

__all__ = ['DiameterMetric']


@dataclass(frozen=False)
class DiameterMetric(ArchitectingMetric):
    """Representing the maximum engine diameter as design goal or constraint."""

    max_diameter: float = 4  # [m], if used as a constraint

    # Specify the operating condition to extract from, otherwise will take the design condition
    condition: OperatingCondition = None

    def get_opt_objectives(self, choices: List[ArchitectingChoice]) -> List[Objective]:
        return [Objective('diameter_obj', ObjectiveDirection.MINIMIZE)]

    def get_opt_constraints(self, choices: List[ArchitectingChoice]) -> List[Constraint]:
        return [Constraint('diameter_con', ConstraintDirection.LOWER_EQUAL_THAN, limit_value=self.max_diameter)]

    def get_opt_metrics(self, choices: List[ArchitectingChoice]) -> List[OutputMetric]:
        return [OutputMetric('diameter_met')]

    def extract_met(self, analysis_problem: AnalysisProblem, result: OperatingMetricsMap, architecture: TurbofanArchitecture) -> Sequence[float]:
        return [self._get_diameter(analysis_problem, result, architecture)]

    def _get_diameter(self, analysis_problem: AnalysisProblem, result: OperatingMetricsMap, architecture: TurbofanArchitecture):
        ops_metrics = result[analysis_problem.design_condition] if self.condition is None else result[self.condition]
        return Diameter(ops_metrics, architecture).diameter_calculation()[0]  # get maximum engine diameter as metric
