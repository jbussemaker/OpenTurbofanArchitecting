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

import numpy as np
from typing import *
from dataclasses import dataclass
from open_turb_arch.architecting.choice import *
from open_turb_arch.evaluation.analysis.builder import *
from open_turb_arch.evaluation.architecture.flow import *
from open_turb_arch.evaluation.architecture.turbomachinery import *

__all__ = ['IntercoolerChoice']


@dataclass(frozen=False)
class IntercoolerChoice(ArchitectingChoice):
    """Represents the choices of whether to include an intercooler or not."""

    fix_include_ic: bool = None  # Set to True of False to fix the choice of whether to include an intercooler or not

    fix_ic_location: int = None  # Fix the location of the intercooler

    fixed_radius: float = None  # Fix the radius of each intercooler pipe
    radius_bounds: Tuple[float, float] = (0.01, 0.25)  # Pipe radius design bounds (verify & validate!!)

    fixed_length: float = None  # Fix the length of each intercooler pipe
    length_bounds: Tuple[float, float] = (0.01, 1)  # Intercooler pipe length bounds

    fixed_number: int = None  # Fix the number of intercooler pipes

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            DiscreteDesignVariable(
                'include_ic', type=DiscreteDesignVariableType.CATEGORICAL, values=[False, True],
                fixed_value=self.fix_include_ic),

            DiscreteDesignVariable(
                'ic_location', type=DiscreteDesignVariableType.INTEGER, values=[0, 1, 2],
                fixed_value=self.fix_ic_location),

            ContinuousDesignVariable(
                'radius', bounds=self.radius_bounds, fixed_value=self.fixed_radius),

            ContinuousDesignVariable(
                'length', bounds=self.length_bounds, fixed_value=self.fixed_length),

            DiscreteDesignVariable(
                'number', type=DiscreteDesignVariableType.INTEGER, values=range(1, 17),
                fixed_value=self.fixed_number),
        ]

    def get_construction_order(self) -> int:
        return 9

    def modify_architecture(self, architecture: TurbofanArchitecture, analysis_problem: AnalysisProblem, design_vector: DecodedDesignVector) \
            -> Sequence[Union[bool, DecodedValue]]:

        # Check if fan is present
        fan_present = False
        compressors = architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan':
                fan_present = True

        # The intercooler choice is only active if a fan is included
        include_ic, ic_location, radius, length, number = design_vector

        # Modify intercooler location based on number of turbines
        turbines = len(architecture.get_elements_by_type(Turbine))
        modified_ic_location = ic_location if ic_location <= turbines-1 else turbines-1

        is_active = [fan_present, modified_ic_location, fan_present and include_ic, fan_present and include_ic, fan_present and include_ic]

        if fan_present and include_ic == 1:
            self._include_ic(architecture, modified_ic_location, radius, length, number)

        return is_active

    @staticmethod
    def _include_ic(architecture: TurbofanArchitecture, location: int, radius: float, length: float, number: int):

        # Find necessary elements
        compressor = architecture.get_elements_by_type(Compressor)[-1-1*location]
        fan_splitter = architecture.get_elements_by_type(Splitter)[0]

        # Calculate heat exchanger area and overall transfer coefficient
        area = 2*np.pi*radius*length*number*1550  # inch2
        h_overall = 0.00002

        # Create new elements: the intercooler
        intercooler = HeatExchanger(
            name='intercooler', fluid=compressor, coolant=fan_splitter, area=area, h_overall=h_overall
        )

        # Reroute flows
        intercooler.target_fluid = compressor.target
        intercooler.target_coolant = fan_splitter.target_bypass
        compressor.flow_out = 'Fl_I1'
        compressor.target = intercooler
        fan_splitter.flow_out = 'Fl_I2'
        fan_splitter.target_bypass = intercooler

        # Add intercooler to the architecture elements
        architecture.elements.insert(architecture.elements.index(compressor)+1, intercooler)
