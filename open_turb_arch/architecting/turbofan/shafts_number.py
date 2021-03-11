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
from open_turb_arch.evaluation.analysis.builder import *
from open_turb_arch.evaluation.architecture.flow import *
from open_turb_arch.evaluation.architecture.turbomachinery import *

__all__ = ['ShaftChoice']


@dataclass(frozen=False)
class ShaftChoice(ArchitectingChoice):
    """Represents the choices of how many shafts to use in the engine."""

    fixed_add_shafts: int = None  # Fix the number of added shafts

    fixed_pr_compressor_ip: float = None  # Fix the IP compressor pressure ratio
    pr_compressor_ip_bounds: Tuple[float, float] = (1, 10)  # IP compressor pressure ratio bounds

    fixed_pr_compressor_lp: float = None  # Fix the LP compressor pressure ratio
    pr_compressor_lp_bounds: Tuple[float, float] = (1, 10)  # LP compressor pressure ratio bounds

    fixed_rpm_shaft_ip: float = None  # Fix the IP shaft rpm
    rpm_shaft_ip_bounds: Tuple[float, float] = (1000, 20000)  # IP shaft rpm bounds

    fixed_rpm_shaft_lp: float = None  # Fix the LP shaft rpm
    rpm_shaft_lp_bounds: Tuple[float, float] = (1000, 20000)  # LP shaft rpm bounds

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            DiscreteDesignVariable(
                'number_shafts', type=DiscreteDesignVariableType.INTEGER, values=[0, 1, 2],
                fixed_value=self.fixed_add_shafts),

            ContinuousDesignVariable(
                'pr_compressor_ip', bounds=self.pr_compressor_ip_bounds,
                fixed_value=self.fixed_pr_compressor_ip),

            ContinuousDesignVariable(
                'pr_compressor_lp', bounds=self.pr_compressor_lp_bounds,
                fixed_value=self.fixed_pr_compressor_lp),

            ContinuousDesignVariable(
                'rpm_shaft_ip', bounds=self.rpm_shaft_ip_bounds,
                fixed_value=self.fixed_rpm_shaft_ip),

            ContinuousDesignVariable(
                'rpm_shaft_lp', bounds=self.rpm_shaft_lp_bounds,
                fixed_value=self.fixed_rpm_shaft_lp),
        ]

    def get_construction_order(self) -> int:
        return 1

    def modify_architecture(self, architecture: TurbofanArchitecture, analysis_problem: AnalysisProblem, design_vector: DecodedDesignVector) \
            -> Sequence[Union[bool, DecodedValue]]:

        # The number of added shafts is always active
        number_shafts, pr_compressor_ip, pr_compressor_lp, rpm_shaft_ip, rpm_shaft_lp = design_vector
        is_active = [True, number_shafts >= 1, number_shafts == 2, number_shafts >= 1, number_shafts == 2]

        pr_compressor = [pr_compressor_ip, pr_compressor_lp]
        rpm_shaft = [rpm_shaft_ip, rpm_shaft_lp]
        for shaft in range(0, number_shafts):
            self._add_shafts(architecture, shaft, pr_compressor[shaft], rpm_shaft[shaft])

        return is_active

    @staticmethod
    def _add_shafts(architecture: TurbofanArchitecture, number: int, pr_compressor: float, rpm_shaft: float):

        # Find necessary elements
        inlet = architecture.get_elements_by_type(Inlet)[0]
        compressor = architecture.get_elements_by_type(Compressor)[0]
        turbine = architecture.get_elements_by_type(Turbine)[number]
        nozzle = architecture.get_elements_by_type(Nozzle)[0]
        shaft = architecture.get_elements_by_type(Shaft)[0]

        # Define names for added shafts
        if number == 0:
            shaft_name = 'ip'
        elif number == 1:
            shaft_name = 'lp'
        else:
            raise RuntimeError('Unexpected number of shafts %s' % number)

        # Create new elements: compressor, turbine and shaft
        comp_new = Compressor(
            name='comp_'+shaft_name, map=CompressorMap.AXI_5,
            mach=.4578, pr=pr_compressor, eff=.89,
        )

        turb_new = Turbine(
            name='turb_'+shaft_name, map=TurbineMap.LPT_2269,
            mach=.4578, eff=.89,
        )

        shaft_new = Shaft(
            name='shaft_'+shaft_name, connections=[comp_new, turb_new],
            rpm_design=rpm_shaft, power_loss=0.,
        )

        # Insert compressor, turbine and shaft into architecture elements list
        architecture.elements.insert(architecture.elements.index(compressor), comp_new)
        architecture.elements.insert(architecture.elements.index(turbine)+1, turb_new)
        architecture.elements.insert(architecture.elements.index(shaft), shaft_new)

        # Reroute flow from inlet and new compressor
        inlet.target = comp_new
        comp_new.target = compressor

        # Reroute flow to new turbine and nozzle
        turbine.target = turb_new
        turb_new.target = nozzle
