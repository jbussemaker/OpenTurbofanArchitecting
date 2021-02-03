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

__all__ = ['FanGearChoice']


@dataclass(frozen=False)
class FanGearChoice(ArchitectingChoice):
    """Represents the choices of whether to include a fan or not and which bypass ratio and fan pressure ratio to use
    if yes. Next to that, the choice for a gearbox or not can be made as well."""

    fix_include_fan: bool = None  # Set to True of False to fix the choice of whether to include a fan or not

    fixed_bpr: float = None  # Fix the bypass ratio
    bpr_bounds: Tuple[float, float] = (2., 15.)  # Bypass ratio design bounds

    fixed_fpr: float = None  # Fix the fan pressure ratio
    fpr_bounds: Tuple[float, float] = (1.1, 1.8)

    fix_include_gear: bool = None  # Set to True of False to fix the choice of whether to include a gear or not

    fixed_gear: float = None  # Fix the gear ratio
    gear_bounds: Tuple[float, float] = (1., 5.)  # Gear ratio design bounds (verify & validate!!)

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            IntegerDesignVariable(
                'include_fan', type=IntDesignVariableType.CATEGORICAL, values=[False, True],
                fixed_value=self.fix_include_fan),

            ContinuousDesignVariable(
                'bpr', bounds=self.bpr_bounds, fixed_value=self.fixed_bpr),

            ContinuousDesignVariable(
                'fpr', bounds=self.fpr_bounds, fixed_value=self.fixed_fpr),
            
            IntegerDesignVariable(
                'include_gear', type=IntDesignVariableType.CATEGORICAL, values=[False, True],
                fixed_value=self.fix_include_gear),
            
            ContinuousDesignVariable(
                'gear_ratio', bounds=self.gear_bounds, fixed_value=self.fixed_gear)
        ]

    def get_construction_order(self) -> int:
        return 0

    def modify_architecture(self, architecture: TurbofanArchitecture, design_vector: DecodedDesignVector) \
            -> Sequence[bool]:

        # The BPR and FPR design variables are only active if a fan is included
        include_fan, bpr, fpr, include_gear, gear_ratio = design_vector
        is_active = [True, include_fan, include_fan, True, include_gear]

        if include_fan:
            self._include_fan(architecture, bpr, fpr, include_gear=include_gear, gear_ratio=gear_ratio)

        return is_active

    def _include_fan(self, architecture: TurbofanArchitecture, bpr: float, fpr: float, include_gear: bool, gear_ratio: float):

        # Create new elements: the fan and the bypass flow
        fan = Compressor(
            name='fan', map=CompressorMap.AXI_5,
            mach=.4578, pr=fpr, eff=.89,
        )

        fan.target = splitter = Splitter(
            name='splitter', bpr=bpr,
            core_mach=.3, bypass_mach=.45,
        )

        splitter.target_bypass = bypass_nozzle = Nozzle(
            name='bypass_nozzle', type=NozzleType.CV,
            v_loss_coefficient=.99, fuel_in_air=False,
        )

        architecture.elements += [fan, splitter, bypass_nozzle]

        # Find inlet
        inlet = architecture.get_elements_by_type(Inlet)[0]
        compressor = inlet.target

        # Reroute flow from inlet
        inlet.target = fan
        splitter.target_core = compressor

        if include_gear:
            self._include_gear(architecture, gear_ratio)
        elif not include_gear:
            # Connect fan to shaft
            shaft = architecture.get_elements_by_type(Shaft)[-1]
            shaft.connections.append(fan)

    @staticmethod
    def _include_gear(architecture: TurbofanArchitecture, gear_ratio: float):

        fan = architecture.get_elements_by_type(Compressor)[-1]
        lp_shaft = architecture.get_elements_by_type(Shaft)[-1]
        lp_shaft.geared = GearOption.Gear

        # Create new elements: the fan shaft and gearbox
        fan_shaft = Shaft(
            name='fan_shaft', connections=[fan]
        )

        gearbox = Gearbox(
            name='gearbox', connections=[fan_shaft, lp_shaft]
        )

        architecture.elements += [fan_shaft, gearbox]
