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
from open_turb_arch.evaluation.architecture import *

__all__ = ['LengthMetric']


@dataclass(frozen=False)
class LengthMetric(ArchitectingMetric):
    """Representing the engine length as design goal or constraint."""

    max_length: float = 4  # [m], if used as a constraint

    # Specify the operating condition to extract from, otherwise will take the design condition
    condition: OperatingCondition = None

    def get_opt_objectives(self, choices: List[ArchitectingChoice]) -> List[Objective]:
        return [Objective('length_obj', ObjectiveDirection.MINIMIZE)]

    def get_opt_constraints(self, choices: List[ArchitectingChoice]) -> List[Constraint]:
        return [Constraint('length_con', ConstraintDirection.LOWER_EQUAL_THAN, limit_value=self.max_length)]

    def get_opt_metrics(self, choices: List[ArchitectingChoice]) -> List[OutputMetric]:
        return [OutputMetric('length_met')]

    def extract_met(self, analysis_problem: AnalysisProblem, result: OperatingMetricsMap, architecture: TurbofanArchitecture) -> Sequence[float]:
        return [self._get_length(analysis_problem, result, architecture)]

    def _get_length(self, analysis_problem: AnalysisProblem, result: OperatingMetricsMap, architecture: TurbofanArchitecture):

        # Check whether gearbox is present
        gear = architecture.get_elements_by_type(Gearbox) is not None

        # Check if fan is present
        fan_present = False
        compressors = architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan':
                fan_present = True

        # Get massflow rate and OPR
        ops_metrics = result[analysis_problem.design_condition] if self.condition is None else result[self.condition]
        massflow = ops_metrics.mass_flow
        opr = ops_metrics.opr

        # Get BPR
        splitter = architecture.get_elements_by_type(Splitter)
        bpr = splitter[0].bpr if fan_present else 0

        # Calculate length with MIT WATE++ equations
        if not gear:
            a = (6.156*10**2)*bpr**2 + (1.357*10**1)*bpr + 27.51
            b = (6.892*10**(-4))*bpr**2 - (2.714*10**(-2))*bpr + 0.505
            c = 0.129
        else:
            a = (-1.956*10**(-2))*bpr**2 + (1.244*10**0)*bpr + 77.1
            b = (7.354*10**(-6))*bpr**2 - (3.335*10**(-3))*bpr + 0.388
            c = -0.032
        length = (a*(massflow*2.2046226218/100)**b*(opr/40)**c)*0.0254

        # Add length changes based on components
        if len(architecture.get_elements_by_type(Burner)) != 1:     # ITB
            length *= 1.05**(len(architecture.get_elements_by_type(Burner))-1)

        if not fan_present:     # Turbojet
            length *= 0.75
            if len(architecture.get_elements_by_type(Compressor)) != 1:  # Multiple shafts
                length *= 1.1**(len(architecture.get_elements_by_type(Compressor))-1)
        elif fan_present:       # Turbofan
            if len(architecture.get_elements_by_type(Compressor)) != 2:  # Multiple shafts
                length *= 1.1**(len(architecture.get_elements_by_type(Compressor))-2)

        return length
