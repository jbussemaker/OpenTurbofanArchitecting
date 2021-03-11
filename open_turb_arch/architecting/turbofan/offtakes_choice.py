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
    """Represents the choices of offtakes, both power and bleed."""

    fix_power_offtake_location: int = None  # Fix the shaft number of the power offtake

    fix_bleed_offtake_location: int = None  # Fix the compressor number of the bleed offtake

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            DiscreteDesignVariable(
                'power_offtake_location', type=DiscreteDesignVariableType.INTEGER, values=[0, 1, 2],
                fixed_value=self.fix_power_offtake_location),

            DiscreteDesignVariable(
                'bleed_offtake_location', type=DiscreteDesignVariableType.INTEGER, values=[0, 1, 2],
                fixed_value=self.fix_bleed_offtake_location),
        ]

    def get_construction_order(self) -> int:
        return 9

    def modify_architecture(self, architecture: TurbofanArchitecture, analysis_problem: AnalysisProblem, design_vector: DecodedDesignVector) \
            -> Sequence[Union[bool, DecodedValue]]:

        # Find the number of shafts present
        shafts = len(architecture.get_elements_by_type(Shaft))

        # The power and bleed offtake locations are true if shaft choice is smaller then or equal to then the number of shafts in architecture
        power_offtake_location, bleed_offtake_location = design_vector
        is_active = [True, True]

        # Add offtakes
        self._power_location(architecture, analysis_problem, power_offtake_location)
        # self._bleed_location(architecture, analysis_problem, bleed_offtake_location)

        return is_active

    @staticmethod
    def _power_location(architecture: TurbofanArchitecture, analysis_problem: AnalysisProblem, shaft_number: int):

        # Find the required shaft for power offtake
        shafts = len(architecture.get_elements_by_type(Shaft))
        if shafts >= shaft_number+1:  # Feasible shaft selection
            shaft = architecture.get_elements_by_type(Shaft)[-1-1*shaft_number]
        else:  # Unfeasible shaft selection: choose closest one
            shaft = architecture.get_elements_by_type(Shaft)[-1*shafts]

        # Add the power offtake to the shaft
        shaft.offtake_shaft = True
        shaft.power_offtake = analysis_problem.design_condition.power_offtake

    @staticmethod
    def _bleed_location(architecture: TurbofanArchitecture, analysis_problem: AnalysisProblem, compressor_number: int):

        burner = architecture.get_elements_by_type(Burner)[0]

        # Find the required shaft for power offtake
        compressors = len(architecture.get_elements_by_type(Compressor))
        if compressors >= compressor_number+1:  # Feasible compressor selection
            source = architecture.get_elements_by_type(Compressor)[-1-1*compressor_number]
            target = source.target if source.name != 'compressor' else burner
        else:  # Unfeasible compressor selection: choose closest one
            source = architecture.get_elements_by_type(Compressor)[-1*compressors]
            target = source.target if source.name != 'compressor' else burner

        # # Add bleed offtake to architecture
        # bleed_offtake = BleedInter(
        #     name='bleed_offtake', target=target, bleed_names=['bleed_offtake']
        # )
        #
        # # Reroute flows
        # source.target = bleed_offtake
        #
        # # Add BleedInter to architecture elements
        # architecture.elements.insert(architecture.elements.index(source)+1, bleed_offtake)

        source.offtake_bleed = True
        source.bleed_names.append('bleed_offtake')
        source.bleed_frac_w = 0.05

        # # Add the bleed offtake to the compressor
        # bleed_offtake = BleedIntra(
        #     name='bleed_offtake', source=compressor, bleed_names=['bleed_offtake'],
        # )
        #
        # # Add BleedIntra to architecture elements
        # architecture.elements.insert(architecture.elements.index(compressor), bleed_offtake)
