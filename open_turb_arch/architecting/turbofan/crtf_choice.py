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

__all__ = ['CRTFChoice']


@dataclass(frozen=False)
class CRTFChoice(ArchitectingChoice):
    """Represents the choices of whether to include a counter-rotating fan or not and which bypass ratio and fan pressure
    ratio to use if yes."""

    fix_include_crtf: bool = None  # Set to True of False to fix the choice of whether to include a CR fan or not

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            DiscreteDesignVariable(
                'include_crtf_fan', type=DiscreteDesignVariableType.CATEGORICAL, values=[False, True],
                fixed_value=self.fix_include_crtf),
            ]

    def get_construction_order(self) -> int:
        return 4

    def modify_architecture(self, architecture: TurbofanArchitecture, analysis_problem: AnalysisProblem, design_vector: DecodedDesignVector) \
            -> Sequence[Union[bool, DecodedValue]]:

        # Check if fan is present
        fan_present = False
        compressors = architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan':
                fan_present = True

        # The CRTF choice is only active if a fan is included
        [include_crtf_fan] = design_vector
        is_active = [fan_present]

        if fan_present and include_crtf_fan == 1:
            self._include_crtf_fan(architecture)

        return is_active

    @staticmethod
    def _include_crtf_fan(architecture: TurbofanArchitecture):

        # Find fan
        fan = None
        compressors = architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan':
                fan = architecture.get_elements_by_type(Compressor)[compressor]

        # Create new element: CRTF
        crtf = Compressor(
            name='crtf', map=fan.map,
            mach=fan.mach, pr=fan.pr, eff=fan.eff
        )

        # Reroute flows
        inlet = architecture.get_elements_by_type(Inlet)[0]
        inlet.target = crtf
        crtf.target = fan

        # Insert CRTF into architecture elements list
        architecture.elements.insert(architecture.elements.index(fan), crtf)

        # Connect fan to shaft
        shaft = architecture.get_elements_by_type(Shaft)[0]
        shaft.connections.append(crtf)
