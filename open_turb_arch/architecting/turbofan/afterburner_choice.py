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

__all__ = ['AfterburnerChoice']


@dataclass(frozen=False)
class AfterburnerChoice(ArchitectingChoice):
    """Represents the choices of whether to include an afterburner or not."""

    fix_include_afterburner: bool = None  # Set to True of False to fix the choice of whether to include an afterburner or not

    fixed_far: float = None  # Fix the FAR of the afterburner
    far_bounds: Tuple[float, float] = (0., 0.05)  # FAR design bounds (verify & validate!!)

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            DiscreteDesignVariable(
                'include_afterburner', type=DiscreteDesignVariableType.CATEGORICAL, values=[False, True],
                fixed_value=self.fix_include_afterburner),

            ContinuousDesignVariable(
                'far', bounds=self.far_bounds, fixed_value=self.fixed_far),

            ]

    def get_construction_order(self) -> int:
        return 5

    def modify_architecture(self, architecture: TurbofanArchitecture, analysis_problem: AnalysisProblem, design_vector: DecodedDesignVector) \
            -> Sequence[Union[bool, DecodedValue]]:

        # Check if fan is present
        fan_present = False
        compressors = architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan':
                fan_present = True

        # The afterburner choice is only active if no fan is included
        include_afterburner, far = design_vector
        is_active = [(not fan_present), (not fan_present and include_afterburner)]

        if include_afterburner and not fan_present:
            self._include_afterburner(architecture, far)

        return is_active

    @staticmethod
    def _include_afterburner(architecture: TurbofanArchitecture, far: float):

        # Find necessary elements
        turbine = architecture.get_elements_by_type(Turbine)[-1]
        nozzle = architecture.get_elements_by_type(Nozzle)[0]
        fuel_type = architecture.get_elements_by_type(Burner)[0].fuel  # Same fuel type as normal burner

        # Create new elements: the afterburner
        afterburner = Burner(
            name='afterburner', fuel=fuel_type, fuel_in_air=True, main=False, far=far
        )

        # Reroute flows
        turbine.target = afterburner
        afterburner.target = nozzle

        # Add afterburner to the architecture elements
        architecture.elements.insert(architecture.elements.index(turbine)+1, afterburner)
