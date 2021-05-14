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
from open_turb_arch.architecting.opt_defs import *
from open_turb_arch.evaluation.analysis.builder import *
from open_turb_arch.evaluation.architecture.flow import *
from open_turb_arch.evaluation.architecture.turbomachinery import *

__all__ = ['ShaftChoice']


@dataclass(frozen=False)
class ShaftChoice(ArchitectingChoice):
    """Represents the choices of how many shafts to use in the engine."""

    fixed_number_shafts: int = None  # Fix the number of added shafts

    fixed_opr: float = None  # Fix the overall pressure ratio of the engine
    opr_bounds: Tuple[float, float] = (1.1, 60)  # Overall pressure ratio bounds

    fixed_pr_compressor_ip: float = None  # Fix the percentage the IP performs from the overall core pressure ratio
    fixed_pr_compressor_lp: float = None  # Fix the percentage the LP performs from the overall core pressure ratio

    pr_compressor_bounds: Tuple[float, float] = (0.1, 0.9)  # Percentage pressure ratio bounds

    fixed_rpm_shaft_hp: float = None  # Fix the HP shaft rpm
    fixed_rpm_shaft_ip: float = None  # Fix the IP shaft rpm
    fixed_rpm_shaft_lp: float = None  # Fix the LP shaft rpm

    rpm_shaft_bounds: Tuple[float, float] = (1000, 20000)  # Shaft rpm bounds

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            DiscreteDesignVariable(
                'number_shafts', type=DiscreteDesignVariableType.INTEGER, values=[1, 2, 3],
                fixed_value=self.fixed_number_shafts),

            ContinuousDesignVariable(
                'opr', bounds=self.opr_bounds,
                fixed_value=self.fixed_opr),

            ContinuousDesignVariable(
                'pr_compressor_ip', bounds=self.pr_compressor_bounds,
                fixed_value=self.fixed_pr_compressor_ip),

            ContinuousDesignVariable(
                'pr_compressor_lp', bounds=self.pr_compressor_bounds,
                fixed_value=self.fixed_pr_compressor_lp),

            ContinuousDesignVariable(
                'rpm_shaft_hp', bounds=self.rpm_shaft_bounds,
                fixed_value=self.fixed_rpm_shaft_hp),

            ContinuousDesignVariable(
                'rpm_shaft_ip', bounds=self.rpm_shaft_bounds,
                fixed_value=self.fixed_rpm_shaft_ip),

            ContinuousDesignVariable(
                'rpm_shaft_lp', bounds=self.rpm_shaft_bounds,
                fixed_value=self.fixed_rpm_shaft_lp),
        ]

    def get_construction_order(self) -> int:
        return 3

    def modify_architecture(self, architecture: TurbofanArchitecture, analysis_problem: AnalysisProblem, design_vector: DecodedDesignVector) \
            -> Sequence[Union[bool, DecodedValue]]:

        # Check if fan is present
        fan_present = crtf_present = False
        fan_opr = crtf_opr = 1
        compressors = architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan':
                fan_present = True
                fan_opr = compressors[compressor].pr
            if compressors[compressor].name == 'crtf':
                crtf_present = True
                crtf_opr = compressors[compressor].pr

        # The number of added shafts is always active
        number_shafts, opr, pr_compressor_ip, pr_compressor_lp, rpm_shaft_hp, rpm_shaft_ip, rpm_shaft_lp = design_vector
        rpm_shaft = [rpm_shaft_hp, rpm_shaft_ip, rpm_shaft_lp]
        opr_core = opr/fan_opr/crtf_opr

        # Check the pressure ratio percentages
        pr_percentages = [pr_compressor_ip if number_shafts >= 2 else 0, pr_compressor_lp if number_shafts == 3 else 0]
        pr_percentages = [1/3, 1/3] if pr_percentages[0]+pr_percentages[1] >= 1 else pr_percentages

        # Calculate the pressure ratio for each compressor based on number of shafts and pressure ratio percentages
        if pr_percentages[0] == 0 and pr_percentages[1] == 0:  # 1 shaft
            pr_base = opr_core
        elif pr_percentages[1] == 0:  # 2 shafts
            pr_base = (opr_core/(pr_percentages[0]-pr_percentages[0]**2))**(1/2)
        else:  # 3 shafts
            pr_base = (opr_core/(pr_percentages[0]*pr_percentages[1]-pr_percentages[0]**2*pr_percentages[1]-pr_percentages[0]*pr_percentages[1]**2))**(1/3)
        pr_compressor = [pr_base*(1-pr_percentages[0]-pr_percentages[1]), pr_base*pr_percentages[0], pr_base*pr_percentages[1]]

        is_active = [True, True, pr_percentages[0], pr_percentages[1], True, number_shafts >= 2, number_shafts == 3]

        self._add_shafts(architecture, number_shafts-1, pr_compressor, rpm_shaft, fan_present, crtf_present)

        return is_active

    def get_constraints(self) -> Optional[List[Constraint]]:
        # Max sum of pressure ratio percentages is 0.9 to enable at least 10% for the LP compressor
        return [Constraint('max_pr_percentages_sum', ConstraintDirection.LOWER_EQUAL_THAN, 0.9)]

    def evaluate_constraints(self, architecture: TurbofanArchitecture, design_vector: DecodedDesignVector,
                             an_problem: AnalysisProblem, result: OperatingMetricsMap) -> Optional[Sequence[float]]:
        # Sum the pressure ratio percentages
        pr_percentages_sum = sum(design_vector[2:3])
        return [pr_percentages_sum]

    @staticmethod
    def _add_shafts(architecture: TurbofanArchitecture, number_shafts: int, pr_compressor: list, rpm_shaft: list, fan_present: bool, crtf_present: bool):

        # Find the inlet, HP compressor and HP shaft
        inlet = architecture.get_elements_by_type(Inlet)[0]
        compressor = architecture.get_elements_by_type(Compressor)[-1]
        shaft = architecture.get_elements_by_type(Shaft)[-1]

        # Adjust the HP compressor pressure ratio and shaft rpm
        compressor.pr = pr_compressor[0]
        shaft.rpm_design = rpm_shaft[0]

        for number in range(0, number_shafts):

            # Find necessary elements
            compressor = architecture.get_elements_by_type(Compressor)[-1-1*number]
            turbine = architecture.get_elements_by_type(Turbine)[number]
            nozzle = architecture.get_elements_by_type(Nozzle)[0]
            shaft = architecture.get_elements_by_type(Shaft)[0]

            # Define names for added shafts
            shaft_name = 'ip' if number == 0 else 'lp'

            # Create new elements: compressor, turbine and shaft
            comp_new = Compressor(
                name='comp_'+shaft_name, map=CompressorMap.AXI_5,
                mach=compressor.mach*1.15, pr=pr_compressor[number+1], eff=compressor.eff,
            )

            turb_new = Turbine(
                name='turb_'+shaft_name, map=TurbineMap.LPT_2269,
                mach=turbine.mach*1.15, eff=turbine.eff,
            )

            shaft_new = Shaft(
                name='shaft_'+shaft_name, connections=[comp_new, turb_new],
                rpm_design=rpm_shaft[number+1], power_loss=0.,
            )

            # Insert compressor, turbine and shaft into architecture elements list
            architecture.elements.insert(architecture.elements.index(compressor), comp_new)
            architecture.elements.insert(architecture.elements.index(turbine)+1, turb_new)
            architecture.elements.insert(architecture.elements.index(shaft), shaft_new)

            # Reroute flow from inlet and new compressor
            comp_new.target = compressor

            # Reroute flow to new turbine and nozzle
            turbine.target = turb_new
            turb_new.target = nozzle

        # Find elements
        hp_shaft = architecture.get_elements_by_type(Shaft)[-1]
        lp_shaft = architecture.get_elements_by_type(Shaft)[0]
        lp_comp = architecture.get_elements_by_type(Compressor)[fan_present+crtf_present]

        if fan_present:
            fan = architecture.get_elements_by_type(Compressor)[crtf_present]

            # Disconnect fan from original shaft
            del hp_shaft.connections[hp_shaft.connections.index(fan)]

            # Recouple fan to low pressure shaft
            lp_shaft.connections.append(fan)

            # Reroute flows
            splitter = architecture.get_elements_by_type(Splitter)[0]
            splitter.target_core = lp_comp

        if crtf_present:
            crtf = architecture.get_elements_by_type(Compressor)[0]

            # Disconnect crtf from original shaft
            del hp_shaft.connections[hp_shaft.connections.index(crtf)]

            # Recouple fan to low pressure shaft
            lp_shaft.connections.append(crtf)

        # Reroute inlet flow
        inlet.target = architecture.get_elements_by_type(Compressor)[0]
