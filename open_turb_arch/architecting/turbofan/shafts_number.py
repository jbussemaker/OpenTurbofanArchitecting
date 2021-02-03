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
from open_turb_arch.evaluation.architecture.flow import *
from open_turb_arch.evaluation.architecture.turbomachinery import *

__all__ = ['ShaftChoice']


@dataclass(frozen=False)
class ShaftChoice(ArchitectingChoice):
    """Represents the choices of how many shafts to use in the engine."""

    fixed_add_shafts: int = None  # Fix the number of shafts

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            IntegerDesignVariable(
                'number_shafts', type=IntDesignVariableType.DISCRETE, values=[0, 1, 2],
                fixed_value=self.fixed_add_shafts),
        ]

    def get_construction_order(self) -> int:
        return 0

    def modify_architecture(self, architecture: TurbofanArchitecture, design_vector: DecodedDesignVector) \
            -> Sequence[bool]:

        # The number of added shaft is always active
        number_shafts = design_vector
        is_active = [number_shafts]

        for shaft in range(0, number_shafts[0]):
            self._add_shafts(architecture, shaft)

        return is_active

    @staticmethod
    def _add_shafts(architecture: TurbofanArchitecture, number: int):

        # Find necessary elements
        inlet = architecture.get_elements_by_type(Inlet)[0]
        compressor = architecture.get_elements_by_type(Compressor)[number]
        turbine = architecture.get_elements_by_type(Turbine)[number]
        nozzle = architecture.get_elements_by_type(Nozzle)[0]

        if number == 0:
            shaft_name = 'ip'
        elif number == 1:
            shaft_name = 'lp'
        else:
            raise RuntimeError('Unexpected number of shafts %s')

        # Create new element: compressor and turbine
        comp = Compressor(
            name='comp_'+shaft_name, map=CompressorMap.AXI_5,
            mach=.4578, pr=5, eff=.89,
        )

        turb = Turbine(
            name='turb_'+shaft_name, map=TurbineMap.LPT_2269,
            mach=.4578, eff=.89,
        )

        shaft = Shaft(
            name='shaft_'+shaft_name, connections=[comp, turb],
            rpm_design=8070, power_loss=0.,
        )

        architecture.elements += [comp, turb, shaft]

        # Reroute flow from inlet
        inlet.target = comp
        comp.target = compressor

        # Reroute flow to nozzle
        turbine.target = turb
        turb.target = nozzle