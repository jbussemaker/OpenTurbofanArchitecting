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
from open_turb_arch.architecting.opt_defs import *
from open_turb_arch.evaluation.architecture import TurbofanArchitecture

__all__ = ['ArchitectingChoice', 'DesignVariable', 'ContinuousDesignVariable', 'DiscreteDesignVariableType',
           'DiscreteDesignVariable', 'DecodedDesignVector', 'TurbofanArchitecture', 'DecodedValue']


class ArchitectingChoice:
    """Base class representing an architecting choice that can be mapped to one or more design variables and defines
    logic on how to manipulate the architecture definition."""

    def get_design_variables(self) -> List[DesignVariable]:
        raise NotImplementedError

    def get_construction_order(self) -> int:
        """For ordering choices into the order of applying the architecture modifications."""
        raise NotImplementedError

    def modify_architecture(self, architecture: TurbofanArchitecture, design_vector: DecodedDesignVector) \
            -> Sequence[Union[bool, DecodedValue]]:
        """Modify the default turbojet architecture based on the given design vector. Should return for each of the
        design variables whether they are active or not, or an explicit overwritten value of the design variable."""
        raise NotImplementedError
