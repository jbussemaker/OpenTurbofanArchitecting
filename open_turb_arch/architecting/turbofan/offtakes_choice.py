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

import openmdao.api as om
from typing import *
from dataclasses import dataclass
from open_turb_arch.architecting.choice import *
from open_turb_arch.architecting.problem import *
from open_turb_arch.evaluation.analysis.builder import *
from open_turb_arch.evaluation.architecture.flow import *
from open_turb_arch.evaluation.architecture.turbomachinery import *
import open_turb_arch.evaluation.architecture.units as units

__all__ = ['OfftakesChoice']


@dataclass(frozen=False)
class OfftakesChoice(ArchitectingChoice):
    """Represents the choices of offtakes, both power and extraction bleed."""

    fix_power_offtake_location: int = None  # Fix the shaft number of the power offtake

    fix_bleed_offtake_location: int = None  # Fix the compressor number of the extraction bleed offtake

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            DiscreteDesignVariable(
                'power_offtake_location', type=DiscreteDesignVariableType.INTEGER, values=[1, 2, 3],
                fixed_value=self.fix_power_offtake_location),

            DiscreteDesignVariable(
                'bleed_offtake_location', type=DiscreteDesignVariableType.INTEGER, values=[1, 2, 3],
                fixed_value=self.fix_bleed_offtake_location),
        ]

    def get_construction_order(self) -> int:
        return 10

    def modify_architecture(self, architecture: TurbofanArchitecture, analysis_problem: AnalysisProblem, design_vector: DecodedDesignVector) \
            -> Sequence[Union[bool, DecodedValue]]:

        power_offtake_location, bleed_offtake_location = design_vector

        # Find fan shaft
        special_shafts = 0
        shafts = architecture.get_elements_by_type(Shaft)
        for shaft in range(len(shafts)):
            if shafts[shaft].name == 'fan_shaft':
                special_shafts += 1

        # Find fan and CRTF
        special_compressors = 0
        compressors = architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan' or compressors[compressor].name == 'crtf':
                special_compressors += 1

        # Find the required shaft for power offtake
        shafts = len(architecture.get_elements_by_type(Shaft))-special_shafts
        shaft_number = power_offtake_location if shafts >= power_offtake_location else shafts
        shaft = architecture.get_elements_by_type(Shaft)[-shaft_number]

        # Find the required compressor for extraction bleed offtake
        compressors = len(architecture.get_elements_by_type(Compressor))-special_compressors
        compressor_number = bleed_offtake_location if compressors >= bleed_offtake_location else compressors
        compressor = architecture.get_elements_by_type(Compressor)[-compressor_number]

        is_active = [shaft_number, compressor_number]

        # Add offtakes
        self._power_location(analysis_problem, shaft)
        self._bleed_location(architecture, compressor)

        return is_active

    @staticmethod
    def _power_location(analysis_problem: AnalysisProblem, shaft: Shaft):

        # Add the power offtake to the shaft
        shaft.offtake_shaft = True
        shaft.power_offtake = analysis_problem.design_condition.power_offtake

    @staticmethod
    def _bleed_location(architecture: TurbofanArchitecture, compressor: Compressor):

        # Add the bleed offtake to the compressor
        bleed_offtake = BleedIntra(
            name='bleed_offtake', source=compressor, bleed_names=['bleed_offtake_atmos'], source_frac_w=[0.02],
        )
        compressor.offtake_bleed = True
        compressor.bleed_names.append('bleed_offtake_atmos')

        # Add BleedIntra to architecture elements
        architecture.elements.insert(architecture.elements.index(compressor), bleed_offtake)
