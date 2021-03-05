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

__all__ = ['NozzleMixingChoice']


@dataclass(frozen=False)
class NozzleMixingChoice(ArchitectingChoice):
    """Represents the choices of whether to include a separate or mixed nozzle. Only possible if a fan is present already."""

    fix_include_mixing: bool = None  # Set to True of False to fix the choice of whether to use a mixed or separate nozzle

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            DiscreteDesignVariable(
                'include_mixing', type=DiscreteDesignVariableType.CATEGORICAL, values=[False, True],
                fixed_value=self.fix_include_mixing),
        ]

    def get_construction_order(self) -> int:
        return 3        # Executed after the fan_choice

    def modify_architecture(self, architecture: TurbofanArchitecture, design_vector: DecodedDesignVector) \
            -> Sequence[bool]:

        # Check if fan is present
        fan_present = False
        compressors = architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan':
                fan_present = True

        # The mixing choice is only active if a fan is included
        include_mixing = design_vector
        is_active = [fan_present]

        if fan_present and include_mixing == [True]:
            self._include_mixing(architecture)

        return is_active

    @staticmethod
    def _include_mixing(architecture: TurbofanArchitecture):

        # Find core and bypass nozzles
        nozzle_core = architecture.get_elements_by_type(Nozzle)[1]
        nozzle_bypass = architecture.get_elements_by_type(Nozzle)[0]

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

        # Add joint nozzle and mixer to the architecture elements
        architecture.elements.insert(architecture.elements.index(nozzle_core)+1, mixer)
        architecture.elements.insert(architecture.elements.index(mixer)+1, nozzle_joint)
