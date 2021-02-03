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

__all__ = ['FanMixingChoice']


@dataclass(frozen=False)
class FanMixingChoice(ArchitectingChoice):
    """Represents the choices of whether to include a fan or not and which bypass ratio and fan pressure ratio to use
    if yes. Next to that, the choice for a separate or mixed nozzle can be made as well."""

    fix_include_fan: bool = None  # Set to True of False to fix the choice of whether to include a fan or not

    fixed_bpr: float = None  # Fix the bypass ratio
    bpr_bounds: Tuple[float, float] = (2., 15.)  # Bypass ratio design bounds

    fixed_fpr: float = None  # Fix the fan pressure ratio
    fpr_bounds: Tuple[float, float] = (1.1, 1.8)

    fix_include_mixing: bool = None  # Set to True of False to fix the choice of whether to use a mixed or separate nozzle

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
                'include_mixing', type=IntDesignVariableType.CATEGORICAL, values=[False, True],
                fixed_value=self.fix_include_mixing),
        ]

    def get_construction_order(self) -> int:
        return 0

    def modify_architecture(self, architecture: TurbofanArchitecture, design_vector: DecodedDesignVector) \
            -> Sequence[bool]:

        # The BPR and FPR design variables are only active if a fan is included
        include_fan, bpr, fpr, include_mixing = design_vector
        is_active = [True, include_fan, include_fan, include_fan]

        if include_fan:
            self._include_fan(architecture, bpr, fpr, include_mixing=include_mixing)

        return is_active

    def _include_fan(self, architecture: TurbofanArchitecture, bpr: float, fpr: float, include_mixing: bool):

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

        # Connect fan to shaft
        shaft = architecture.get_elements_by_type(Shaft)[-1]
        shaft.connections.append(fan)

        if include_mixing:
            self._include_mixing(architecture)

    @staticmethod
    def _include_mixing(architecture: TurbofanArchitecture):

        nozzle_core = architecture.get_elements_by_type(Nozzle)[0]
        nozzle_bypass = architecture.get_elements_by_type(Nozzle)[1]

        # Create new elements: joint nozzle and mixer
        nozzle_joint = Nozzle(
            name='nozzle_joint', type=NozzleType.CV,
            v_loss_coefficient=.99, fuel_in_air=True
        )

        mixer = Mixer(
            name='mixer', source_1=nozzle_core, source_2=nozzle_bypass,
            target=nozzle_joint
        )

        nozzle_core.flow_out = 'Fl_I1'
        nozzle_core.target = mixer
        nozzle_bypass.flow_out = 'Fl_I2'
        nozzle_bypass.target = mixer

        architecture.elements += [nozzle_joint, mixer]
