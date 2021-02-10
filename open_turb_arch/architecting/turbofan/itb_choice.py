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

__all__ = ['ITBChoice']


@dataclass(frozen=False)
class ITBChoice(ArchitectingChoice):
    """Represents the choices of whether to include an inter-turbine burner or not."""

    fix_include_itb: bool = None  # Set to True of False to fix the choice of whether to include an inter-turbine burner or not

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            IntegerDesignVariable(
                'include_itb', type=IntDesignVariableType.CATEGORICAL, values=[False, True],
                fixed_value=self.fix_include_itb),
            ]

    def get_construction_order(self) -> int:
        return 5        # Executed after the fan_choice

    def modify_architecture(self, architecture: TurbofanArchitecture, design_vector: DecodedDesignVector) \
            -> Sequence[bool]:

        # Check if at least 2 turbines is present
        turbines = architecture.get_elements_by_type(Turbine)
        turbines_present = True if len(turbines) >= 2 else False

        # The inter-turbine burner choice is only active if fan is included
        include_itb = design_vector
        is_active = [include_itb]

        if turbines_present and include_itb == [True]:
            self._include_itb(architecture)

        return is_active

    @staticmethod
    def _include_itb(architecture: TurbofanArchitecture):

        # Find necessary elements
        turbine = architecture.get_elements_by_type(Turbine)[0]
        turbine_ip = architecture.get_elements_by_type(Turbine)[1]
        fuel_type = architecture.get_elements_by_type(Burner)[0].fuel  # Same fuel type as normal burner

        # Create new elements: the inter-turbine burner
        itb = Burner(
            name='itb', fuel=fuel_type, fuel_in_air=True
        )

        # Reroute flows
        turbine.target = itb
        itb.target = turbine_ip

        # Add itb to the architecture elements
        architecture.elements.insert(architecture.elements.index(turbine)+1, itb)