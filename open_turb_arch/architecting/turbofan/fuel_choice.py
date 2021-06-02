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
from open_turb_arch.architecting.choice import *
from open_turb_arch.evaluation.analysis.builder import *
from open_turb_arch.evaluation.architecture.flow import *
from open_turb_arch.evaluation.architecture.turbomachinery import *

__all__ = ['FuelChoice']


@dataclass(frozen=False)
class FuelChoice(ArchitectingChoice):
    """Represents the choice of fuel for the main burner."""

    fix_fuel_type: int = None  # Set to fuel type

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            DiscreteDesignVariable(
                'fuel_type', type=DiscreteDesignVariableType.CATEGORICAL, values=[0, 1, 2, 3, 4],
                fixed_value=self.fix_fuel_type),
            ]

    def get_construction_order(self) -> int:
        return 0

    def modify_architecture(self, architecture: TurbofanArchitecture, analysis_problem: AnalysisProblem, design_vector: DecodedDesignVector) \
            -> Sequence[Union[bool, DecodedValue]]:

        # The fuel type choice is always active
        [fuel_type] = design_vector
        is_active = [True]

        self._select_fuel(architecture, fuel_type)

        return is_active

    @staticmethod
    def _select_fuel(architecture: TurbofanArchitecture, fuel_type: int):

        # Select fuel type
        if fuel_type == 0:
            fuel_choice = FuelType.JET_A
        elif fuel_type == 1:
            fuel_choice = FuelType.JP_7
        elif fuel_type == 2:
            fuel_choice = FuelType.H2
        elif fuel_type == 3:
            fuel_choice = FuelType.CH4
        else:
            fuel_choice = FuelType.H2O

        # Implement the fuel type
        architecture.get_elements_by_type(Burner)[0].fuel = fuel_choice
