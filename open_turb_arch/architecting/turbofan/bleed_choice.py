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
from itertools import *
from dataclasses import dataclass
from open_turb_arch.architecting.choice import *
from open_turb_arch.architecting.opt_defs import *
from open_turb_arch.evaluation.analysis.builder import *
from open_turb_arch.evaluation.architecture.flow import *
from open_turb_arch.evaluation.architecture.turbomachinery import *

__all__ = ['BleedChoice']


@dataclass(frozen=False)
class BleedChoice(ArchitectingChoice):
    """Represents the choices of whether to include bleed or not."""

    # Inter-bleed HPC-burner
    fix_eb_hb_total: float = None  # Fix the total bleed portion of the inter-bleed between the HPC and burner
    fix_eb_hbh_frac_w: float = None  # Fix the bleed portion of the HPT as target of the inter-bleed between the HPC and burner
    fix_eb_hbi_frac_w: float = None  # Fix the bleed portion of the IPT as target of the inter-bleed between the HPC and burner
    fix_eb_hbl_frac_w: float = None  # Fix the bleed portion of the LPT as target of the inter-bleed between the HPC and burner

    # Inter-bleed IPC-HPC
    fix_eb_ih_total: float = None  # Fix the total bleed portion of the inter-bleed between the IPC and HPC
    fix_eb_ihh_frac_w: float = None  # Fix the bleed portion of the HPT as target of the inter-bleed between the IPC and HPC
    fix_eb_ihi_frac_w: float = None  # Fix the bleed portion of the IPT as target of the inter-bleed between the IPC and HPC
    fix_eb_ihl_frac_w: float = None  # Fix the bleed portion of the LPT as target of the inter-bleed between the IPC and HPC

    # Inter-bleed LPC-IPC
    fix_eb_li_total: float = None  # Fix the total bleed portion of the inter-bleed between the LPC and IPC
    fix_eb_lih_frac_w: float = None  # Fix the bleed portion of the HPT as target of the inter-bleed between the LPC and IPC
    fix_eb_lii_frac_w: float = None  # Fix the bleed portion of the IPT as target of the inter-bleed between the LPC and IPC
    fix_eb_lil_frac_w: float = None  # Fix the bleed portion of the LPT as target of the inter-bleed between the LPC and IPC

    # Intra-bleed HPC
    fix_ab_hpc_total: float = None  # Fix the total bleed portion of the HPC intra-bleed
    fix_ab_hh_frac_w: float = None  # Fix the bleed portion of the HPT as target of the HPC intra-bleed
    fix_ab_hi_frac_w: float = None  # Fix the bleed portion of the IPT as target of the HPC intra-bleed
    fix_ab_hl_frac_w: float = None  # Fix the bleed portion of the LPT as target of the HPC intra-bleed

    # Intra-bleed IPC
    fix_ab_ipc_total: float = None  # Fix the total bleed portion of the IPC intra-bleed
    fix_ab_ih_frac_w: float = None  # Fix the bleed portion of the HPT as target of the IPC intra-bleed
    fix_ab_ii_frac_w: float = None  # Fix the bleed portion of the IPT as target of the IPC intra-bleed
    fix_ab_il_frac_w: float = None  # Fix the bleed portion of the LPT as target of the IPC intra-bleed

    # Intra-bleed LPC
    fix_ab_lpc_total: float = None  # Fix the total bleed portion of the LPC intra-bleed
    fix_ab_lh_frac_w: float = None  # Fix the bleed portion of the HPT as target of the LPC intra-bleed
    fix_ab_li_frac_w: float = None  # Fix the bleed portion of the IPT as target of the LPC intra-bleed
    fix_ab_ll_frac_w: float = None  # Fix the bleed portion of the LPT as target of the LPC intra-bleed

    # Bounds of bleed mass flow
    total_bounds: Tuple[float, float] = (0., 0.15)  # Total bleed portion bounds
    frac_w_bounds: Tuple[float, float] = (0., 1.0)  # Bleed portion bounds

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            # Inter-bleed HPC-burner
            ContinuousDesignVariable(
                'eb_hb_total', bounds=self.total_bounds, fixed_value=self.fix_eb_hb_total),
            ContinuousDesignVariable(
                'eb_hbh_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_hbh_frac_w),
            ContinuousDesignVariable(
                'eb_hbi_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_hbi_frac_w),
            ContinuousDesignVariable(
                'eb_hbl_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_hbl_frac_w),

            # Inter-bleed IPC-HPC
            ContinuousDesignVariable(
                'eb_ih_total', bounds=self.total_bounds, fixed_value=self.fix_eb_ih_total),
            ContinuousDesignVariable(
                'eb_ihh_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_ihh_frac_w),
            ContinuousDesignVariable(
                'eb_ihi_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_ihi_frac_w),
            ContinuousDesignVariable(
                'eb_ihl_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_ihl_frac_w),

            # Inter-bleed LPC-IPC
            ContinuousDesignVariable(
                'eb_li_total', bounds=self.total_bounds, fixed_value=self.fix_eb_li_total),
            ContinuousDesignVariable(
                'eb_lih_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_lih_frac_w),
            ContinuousDesignVariable(
                'eb_lii_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_lii_frac_w),
            ContinuousDesignVariable(
                'eb_lil_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_lil_frac_w),

            # Intra-bleed HPC
            ContinuousDesignVariable(
                'ab_hpc_total', bounds=self.total_bounds, fixed_value=self.fix_ab_hpc_total),
            ContinuousDesignVariable(
                'ab_hh_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_hh_frac_w),
            ContinuousDesignVariable(
                'ab_hi_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_hi_frac_w),
            ContinuousDesignVariable(
                'ab_hl_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_hl_frac_w),

            # Intra-bleed IPC
            ContinuousDesignVariable(
                'ab_ipc_total', bounds=self.total_bounds, fixed_value=self.fix_ab_ipc_total),
            ContinuousDesignVariable(
                'ab_ih_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_ih_frac_w),
            ContinuousDesignVariable(
                'ab_ii_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_ii_frac_w),
            ContinuousDesignVariable(
                'ab_il_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_il_frac_w),

            # Intra-bleed LPC
            ContinuousDesignVariable(
                'ab_lpc_total', bounds=self.total_bounds, fixed_value=self.fix_ab_lpc_total),
            ContinuousDesignVariable(
                'ab_lh_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_lh_frac_w),
            ContinuousDesignVariable(
                'ab_li_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_li_frac_w),
            ContinuousDesignVariable(
                'ab_ll_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_ll_frac_w),
        ]

    def get_construction_order(self) -> int:
        return 8

    def modify_architecture(self, architecture: TurbofanArchitecture, analysis_problem: AnalysisProblem, design_vector: DecodedDesignVector) \
            -> Sequence[Union[bool, DecodedValue]]:

        # Check the number of turbines
        turbines = len(architecture.get_elements_by_type(Turbine))
        has_ip = (turbines >= 2)
        has_lp = (turbines == 3)

        eb_hb_total, eb_hbh_frac_w, eb_hbi_frac_w, eb_hbl_frac_w, \
        eb_ih_total, eb_ihh_frac_w, eb_ihi_frac_w, eb_ihl_frac_w, \
        eb_li_total, eb_lih_frac_w, eb_lii_frac_w, eb_lil_frac_w, \
        ab_hpc_total, ab_hh_frac_w, ab_hi_frac_w, ab_hl_frac_w, \
        ab_ipc_total, ab_ih_frac_w, ab_ii_frac_w, ab_il_frac_w, \
        ab_lpc_total, ab_lh_frac_w, ab_li_frac_w, ab_ll_frac_w \
        = design_vector

        totals = [eb_hb_total, eb_ih_total, eb_li_total, ab_hpc_total, ab_ipc_total, ab_lpc_total]
        eb_hb_frac = [eb_hbh_frac_w, eb_hbi_frac_w, eb_hbl_frac_w]
        eb_ih_frac = [eb_ihh_frac_w, eb_ihi_frac_w, eb_ihl_frac_w]
        eb_li_frac = [eb_lih_frac_w, eb_lii_frac_w, eb_lil_frac_w]
        ab_hpc_frac = [ab_hh_frac_w, ab_hi_frac_w, ab_hl_frac_w]
        ab_ipc_frac = [ab_ih_frac_w, ab_ii_frac_w, ab_il_frac_w]
        ab_lpc_frac = [ab_lh_frac_w, ab_li_frac_w, ab_ll_frac_w]

        combined_fracs = [eb_hb_frac, eb_ih_frac, eb_li_frac, ab_hpc_frac, ab_ipc_frac, ab_lpc_frac]
        for i, frac in enumerate(combined_fracs):
            frac[1] = frac[1] if has_ip else 0
            frac[2] = frac[2] if has_lp else 0
            if turbines == 2:
                frac[0], frac[1], frac[2] = (1/2, 1/2, 0.) if frac[0]+frac[1]+frac[2] > 1 else (frac[0], frac[1], frac[2])
            elif turbines == 3:
                frac[0], frac[1], frac[2] = (1/3, 1/3, 1/3) if frac[0]+frac[1]+frac[2] > 1 else (frac[0], frac[1], frac[2])
            frac_atmos = 1-frac[0]-frac[1]-frac[2]
            frac_adjusted = [frac_atmos, frac[0], frac[1], frac[2]]
            combined_fracs[i] = [x*totals[i] for x in frac_adjusted]

        is_active = [True, combined_fracs[0][0], combined_fracs[0][1], combined_fracs[0][2],
                     has_ip, combined_fracs[1][0], combined_fracs[1][1], combined_fracs[1][2],
                     has_lp, combined_fracs[2][0], combined_fracs[2][1], combined_fracs[2][2],
                     True, combined_fracs[3][0], combined_fracs[3][1], combined_fracs[3][2],
                     has_ip, combined_fracs[4][0], combined_fracs[4][1], combined_fracs[4][2],
                     has_lp, combined_fracs[5][0], combined_fracs[5][1], combined_fracs[5][2]]

        # Add the inter-bleed
        self._include_bleed_inter(architecture, combined_fracs[0:3])
        self._include_bleed_intra(architecture, combined_fracs[3:6])

        return is_active

    def get_constraints(self) -> Optional[List[Constraint]]:
        constraints = []
        # Max sum of bleed percentages for all inter- and intra-bleed is 1
        for constraint in range(6):
            bleed_type = 'inter' if constraint <= 2 else 'intra'
            shaft_type = 'hp' if constraint in {0, 3} else ('ip' if constraint in {1, 4} else 'lp')
            con = Constraint('max_bleed_percentages_sum_%s_%s' % (bleed_type, shaft_type), ConstraintDirection.LOWER_EQUAL_THAN, 1)
            constraints.append(con)
        return constraints

    def evaluate_constraints(self, architecture: TurbofanArchitecture, design_vector: DecodedDesignVector,
                             an_problem: AnalysisProblem, result: OperatingMetricsMap) -> Optional[Sequence[float]]:
        constraints = []
        # Sum the bleed percentages per inter- and intra-bleed
        for constraint in range(6):
            bleed_percentages_sum = sum(design_vector[4*constraint+1:4*constraint+4])
            constraints.append(bleed_percentages_sum)
        return constraints

    @staticmethod
    def _include_bleed_inter(architecture: TurbofanArchitecture, fractions: list):

        # Find compressors, burner and turbines
        compressors = architecture.get_elements_by_type(Compressor)
        burner = architecture.get_elements_by_type(Burner)[0]
        turbines = architecture.get_elements_by_type(Turbine)

        for number in range(len(turbines)):

            # Create inter-bleed name
            name = 'bld_inter_' + str(number)

            # Specify targets bleed
            adjusted_targets = []
            bleed_names = []
            if fractions[number][0] != 0:
                adjusted_targets.append('atmos')
                bleed_names.append(name + '_atmos')
            if fractions[number][1] != 0:
                adjusted_targets.append('turbine')
                bleed_names.append(name + '_turbine')
                turbines[0].bleed_names.append(name + '_turbine')
            if fractions[number][2] != 0:
                adjusted_targets.append('turb_ip')
                bleed_names.append(name + '_turb_ip')
                turbines[1].bleed_names.append(name + '_turb_ip')
            if fractions[number][3] != 0:
                adjusted_targets.append('turb_lp')
                bleed_names.append(name + '_turb_lp')
                turbines[2].bleed_names.append(name + '_turb_lp')

            if sum(fractions[number]) != 0:

                # Specify targets bleed-inter component
                target = compressors[-1*number] if number > 0 else burner

                # Create new element(s): BleedInter
                bleed_inter = BleedInter(
                    name=name, target=target, target_bleed=adjusted_targets,
                    bleed_names=bleed_names, source_frac_w=fractions[number]
                )

                # Reroute flows
                compressors[-1-1*number].target = bleed_inter

                # Add BleedInter to architecture elements
                architecture.elements.insert(architecture.elements.index(compressors[-1-1*number])+1, bleed_inter)

    @staticmethod
    def _include_bleed_intra(architecture: TurbofanArchitecture, fractions: list):

        # Find compressors and turbines
        compressors = architecture.get_elements_by_type(Compressor)
        turbines = architecture.get_elements_by_type(Turbine)

        for number in range(len(turbines)):

            # Create intra-bleed name
            name = 'bld_intra_' + str(number)

            # Specify sources bleed-intra component
            source = compressors[-1-1*number]
            source_name = '_hpc' if number == 0 else ('_ipc' if number == 1 else '_lpc')

            # Specify targets bleed
            adjusted_targets = []
            bleed_names = []
            if fractions[number][0] != 0:
                adjusted_targets.append('atmos')
                bleed_names.append(name + source_name + '_atmos')
                compressors[-1-1*number].bleed_names.append(name + source_name + '_atmos')
            if fractions[number][1] != 0:
                adjusted_targets.append('turbine')
                bleed_names.append(name + source_name + '_hp')
                compressors[-1-1*number].bleed_names.append(name + source_name + '_hp')
                turbines[0].bleed_names.append(name + source_name + '_hp')
            if fractions[number][2] != 0:
                adjusted_targets.append('turb_ip')
                bleed_names.append(name + source_name + '_ip')
                compressors[-1-1*number].bleed_names.append(name + source_name + '_ip')
                turbines[1].bleed_names.append(name + source_name + '_ip')
            if fractions[number][3] != 0:
                adjusted_targets.append('turb_lp')
                bleed_names.append(name + source_name + '_lp')
                compressors[-1-1*number].bleed_names.append(name + source_name + '_lp')
                turbines[2].bleed_names.append(name + source_name + '_lp')

            if sum(fractions[number]) != 0:

                # Create new element(s): BleedIntra
                bleed_intra = BleedIntra(
                    name=name, source=source, target=adjusted_targets,
                    bleed_names=bleed_names, source_frac_w=fractions[number]
                )

                # Add BleedIntra to architecture elements
                architecture.elements.insert(architecture.elements.index(compressors[-1-1*number])+1, bleed_intra)
