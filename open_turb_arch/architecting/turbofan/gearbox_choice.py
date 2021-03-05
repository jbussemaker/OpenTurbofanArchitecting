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

__all__ = ['GearboxChoice']


@dataclass(frozen=False)
class GearboxChoice(ArchitectingChoice):
    """Represents the choices of whether to include a gear or not and which gear ratio to use if yes."""

    fix_include_gear: bool = None  # Set to True of False to fix the choice of whether to include a gear or not

    fixed_gear: float = None  # Fix the gear ratio
    gear_bounds: Tuple[float, float] = (1., 5.)  # Gear ratio design bounds (verify & validate!!)

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            DiscreteDesignVariable(
                'include_gear', type=DiscreteDesignVariableType.CATEGORICAL, values=[False, True],
                fixed_value=self.fix_include_gear),

            ContinuousDesignVariable(
                'gear_ratio', bounds=self.gear_bounds, fixed_value=self.fixed_gear),

            ]

    def get_construction_order(self) -> int:
        return 2        # Executed after the fan_choice

    def modify_architecture(self, architecture: TurbofanArchitecture, design_vector: DecodedDesignVector) \
            -> Sequence[bool]:

        # Check if fan is present
        fan_present = False
        compressors = architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan':
                fan_present = True

        # The gearbox choice is only active if a fan is included
        include_gear, gear_ratio = design_vector
        is_active = [fan_present, (fan_present and include_gear)]

        if fan_present and include_gear:
            self._include_gearbox(architecture, gear_ratio=gear_ratio)

        return is_active

    @staticmethod
    def _include_gearbox(architecture: TurbofanArchitecture, gear_ratio: float):

        # Find necessary elements
        fan = architecture.get_elements_by_type(Compressor)[0]
        core_shaft = architecture.get_elements_by_type(Shaft)[0]

        # Disconnect fan from LP_shaft
        del core_shaft.connections[-1]

        # Create new elements: the fan shaft and gearbox
        fan_shaft = Shaft(
            name='fan_shaft', connections=[fan], rpm_design=core_shaft.rpm_design/gear_ratio
        )

        gearbox = Gearbox(
            name='gearbox', core_shaft=core_shaft, fan_shaft=fan_shaft
        )

        core_shaft.connections.append(gearbox)
        fan_shaft.connections.append(gearbox)

        architecture.elements.insert(architecture.elements.index(core_shaft), fan_shaft)
        architecture.elements.insert(architecture.elements.index(fan_shaft), gearbox)
