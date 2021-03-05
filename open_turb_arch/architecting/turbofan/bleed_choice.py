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
from open_turb_arch.evaluation.architecture.flow import *
from open_turb_arch.evaluation.architecture.turbomachinery import *

__all__ = ['BleedChoice']


@dataclass(frozen=False)
class BleedChoice(ArchitectingChoice):
    """Represents the choices of whether to include bleed or not."""

    # List all possible combinations of targets
    _components = ['atmos', 'hpt', 'ipt', 'lpt']
    _options = ['']
    for letter in range(1, len(_components)+1):
        combo = combinations(_components, letter)
        combo = [' '.join(i) for i in combo]
        _options.extend(combo)

    # Inter-bleed HPC-burner
    fix_eb_hb_options: int = None  # Fix the choice for the target(s) of the inter-bleed between the HPC and burner
    fix_eb_hba_frac_w: float = None  # Fix the bleed portion of the atmosphere as target of the inter-bleed between the HPC and burner
    fix_eb_hbh_frac_w: float = None  # Fix the bleed portion of the HPT as target of the inter-bleed between the HPC and burner
    fix_eb_hbi_frac_w: float = None  # Fix the bleed portion of the IPT as target of the inter-bleed between the HPC and burner
    fix_eb_hbl_frac_w: float = None  # Fix the bleed portion of the LPT as target of the inter-bleed between the HPC and burner

    # Inter-bleed IPC-HPC
    fix_eb_ih_options: int = None  # Fix the choice for the target(s) of the inter-bleed between the IPC and HPC
    fix_eb_iha_frac_w: float = None  # Fix the bleed portion of the atmosphere as target of the inter-bleed between the IPC and HPC
    fix_eb_ihh_frac_w: float = None  # Fix the bleed portion of the HPT as target of the inter-bleed between the IPC and HPC
    fix_eb_ihi_frac_w: float = None  # Fix the bleed portion of the IPT as target of the inter-bleed between the IPC and HPC
    fix_eb_ihl_frac_w: float = None  # Fix the bleed portion of the LPT as target of the inter-bleed between the IPC and HPC

    # Inter-bleed LPC-IPC
    fix_eb_li_options: int = None  # Fix the choice for the target(s) of the inter-bleed between the LPC and HPC
    fix_eb_lia_frac_w: float = None  # Fix the bleed portion of the atmosphere as target of the inter-bleed between the LPC and IPC
    fix_eb_lih_frac_w: float = None  # Fix the bleed portion of the HPT as target of the inter-bleed between the LPC and IPC
    fix_eb_lii_frac_w: float = None  # Fix the bleed portion of the IPT as target of the inter-bleed between the LPC and IPC
    fix_eb_lil_frac_w: float = None  # Fix the bleed portion of the LPT as target of the inter-bleed between the LPC and IPC

    # Intra-bleed HPC
    fix_ab_hpc_options: int = None  # Fix the choice for the HPC intra-bleed target(s)
    fix_ab_ha_frac_w: float = None  # Fix the bleed portion of the atmosphere as target of the HPC intra-bleed
    fix_ab_hh_frac_w: float = None  # Fix the bleed portion of the HPT as target of the HPC intra-bleed
    fix_ab_hi_frac_w: float = None  # Fix the bleed portion of the IPT as target of the HPC intra-bleed
    fix_ab_hl_frac_w: float = None  # Fix the bleed portion of the LPT as target of the HPC intra-bleed

    # Intra-bleed IPC
    fix_ab_ipc_options: int = None  # Fix the choice for the IPC intra-bleed target(s)
    fix_ab_ia_frac_w: float = None  # Fix the bleed portion of the atmosphere as target of the IPC intra-bleed
    fix_ab_ih_frac_w: float = None  # Fix the bleed portion of the HPT as target of the IPC intra-bleed
    fix_ab_ii_frac_w: float = None  # Fix the bleed portion of the IPT as target of the IPC intra-bleed
    fix_ab_il_frac_w: float = None  # Fix the bleed portion of the LPT as target of the IPC intra-bleed

    # Intra-bleed LPC
    fix_ab_lpc_options: int = None  # Fix the choice for the LPC intra-bleed target(s)
    fix_ab_la_frac_w: float = None  # Fix the bleed portion of the atmosphere as target of the LPC intra-bleed
    fix_ab_lh_frac_w: float = None  # Fix the bleed portion of the HPT as target of the LPC intra-bleed
    fix_ab_li_frac_w: float = None  # Fix the bleed portion of the IPT as target of the LPC intra-bleed
    fix_ab_ll_frac_w: float = None  # Fix the bleed portion of the LPT as target of the LPC intra-bleed

    # Bounds of bleed mass flow
    frac_w_bounds: Tuple[float, float] = (0.01, 0.1)  # Bleed portion bounds

    def get_design_variables(self) -> List[DesignVariable]:
        return [
            # Inter-bleed HPC-burner
            DiscreteDesignVariable(
                'include_eb_hb_options', type=DiscreteDesignVariableType.CATEGORICAL, values=list(range(len(self._options))),
                fixed_value=self.fix_eb_hb_options),
            ContinuousDesignVariable(
                'eb_hba_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_hba_frac_w),
            ContinuousDesignVariable(
                'eb_hbh_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_hbh_frac_w),
            ContinuousDesignVariable(
                'eb_hbi_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_hbi_frac_w),
            ContinuousDesignVariable(
                'eb_hbl_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_hbl_frac_w),

            # Inter-bleed IPC-HPC
            DiscreteDesignVariable(
                'include_eb_ih_options', type=DiscreteDesignVariableType.CATEGORICAL, values=list(range(len(self._options))),
                fixed_value=self.fix_eb_ih_options),
            ContinuousDesignVariable(
                'eb_iha_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_iha_frac_w),
            ContinuousDesignVariable(
                'eb_ihh_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_ihh_frac_w),
            ContinuousDesignVariable(
                'eb_ihi_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_ihi_frac_w),
            ContinuousDesignVariable(
                'eb_ihl_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_ihl_frac_w),

            # Inter-bleed LPC-IPC
            DiscreteDesignVariable(
                'include_eb_li_options', type=DiscreteDesignVariableType.CATEGORICAL, values=list(range(len(self._options))),
                fixed_value=self.fix_eb_li_options),
            ContinuousDesignVariable(
                'eb_lia_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_lia_frac_w),
            ContinuousDesignVariable(
                'eb_lih_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_lih_frac_w),
            ContinuousDesignVariable(
                'eb_lii_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_lii_frac_w),
            ContinuousDesignVariable(
                'eb_lil_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_eb_lil_frac_w),

            # Intra-bleed HPC
            DiscreteDesignVariable(
                'include_ab_hpc_options', type=DiscreteDesignVariableType.CATEGORICAL, values=list(range(len(self._options))),
                fixed_value=self.fix_ab_hpc_options),
            ContinuousDesignVariable(
                'ab_ha_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_ha_frac_w),
            ContinuousDesignVariable(
                'ab_hh_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_hh_frac_w),
            ContinuousDesignVariable(
                'ab_hi_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_hi_frac_w),
            ContinuousDesignVariable(
                'ab_hl_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_hl_frac_w),

            # Intra-bleed IPC
            DiscreteDesignVariable(
                'include_ab_ipc_options', type=DiscreteDesignVariableType.CATEGORICAL, values=list(range(len(self._options))),
                fixed_value=self.fix_ab_ipc_options),
            ContinuousDesignVariable(
                'ab_ia_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_ia_frac_w),
            ContinuousDesignVariable(
                'ab_ih_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_ih_frac_w),
            ContinuousDesignVariable(
                'ab_ii_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_ii_frac_w),
            ContinuousDesignVariable(
                'ab_il_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_il_frac_w),

            # Intra-bleed LPC
            DiscreteDesignVariable(
                'include_ab_lpc_options', type=DiscreteDesignVariableType.CATEGORICAL, values=list(range(len(self._options))),
                fixed_value=self.fix_ab_lpc_options),
            ContinuousDesignVariable(
                'ab_la_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_la_frac_w),
            ContinuousDesignVariable(
                'ab_lh_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_lh_frac_w),
            ContinuousDesignVariable(
                'ab_li_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_li_frac_w),
            ContinuousDesignVariable(
                'ab_ll_frac_w', bounds=self.frac_w_bounds, fixed_value=self.fix_ab_ll_frac_w),
        ]

    def get_construction_order(self) -> int:
        return 6    # Executed after the fan_choice

    def modify_architecture(self, architecture: TurbofanArchitecture, design_vector: DecodedDesignVector) \
            -> Sequence[bool]:

        # Check the number of turbines
        turbines = len(architecture.get_elements_by_type(Turbine))
        has_ip = (turbines >= 2)
        has_lp = (turbines == 3)

        # Active variables
        include_eb_hb_options, eb_hba_frac_w, eb_hbh_frac_w, eb_hbi_frac_w, eb_hbl_frac_w, \
        include_eb_ih_options, eb_iha_frac_w, eb_ihh_frac_w, eb_ihi_frac_w, eb_ihl_frac_w, \
        include_eb_li_options, eb_lia_frac_w, eb_lih_frac_w, eb_lii_frac_w, eb_lil_frac_w, \
        include_ab_hpc_options, ab_ha_frac_w, ab_hh_frac_w, ab_hi_frac_w, ab_hl_frac_w, \
        include_ab_ipc_options, ab_ia_frac_w, ab_ih_frac_w, ab_ii_frac_w, ab_il_frac_w, \
        include_ab_lpc_options, ab_la_frac_w, ab_lh_frac_w, ab_li_frac_w, ab_ll_frac_w \
        = design_vector

        # Unpack the chosen options
        eb_hb_options = self._options[include_eb_hb_options].split()
        eb_ih_options = self._options[include_eb_ih_options].split()
        eb_li_options = self._options[include_eb_li_options].split()
        ab_hpc_options = self._options[include_ab_hpc_options].split()
        ab_ipc_options = self._options[include_ab_ipc_options].split()
        ab_lpc_options = self._options[include_ab_lpc_options].split()

        # Construct the is_active
        is_active = [True,
                        ('atmos' in eb_hb_options),
                        ('hpt' in eb_hb_options),
                        (has_ip and 'ipt' in eb_hb_options),
                        (has_lp and 'lpt' in eb_hb_options),
                     has_ip,
                        (has_ip and 'atmos' in eb_ih_options),
                        (has_ip and 'hpt' in eb_ih_options),
                        (has_ip and 'ipt' in eb_ih_options),
                        (has_lp and 'lpt' in eb_ih_options),
                     has_lp,
                        (has_lp and 'atmos' in eb_li_options),
                        (has_lp and 'hpt' in eb_li_options),
                        (has_lp and 'ipt' in eb_li_options),
                        (has_lp and 'lpt' in eb_li_options),
                     True,
                        ('atmos' in ab_hpc_options),
                        ('hpt' in ab_hpc_options),
                        (has_ip and 'ipt' in ab_hpc_options),
                        (has_lp and 'lpt' in ab_hpc_options),
                     has_ip,
                        (has_ip and 'atmos' in ab_ipc_options),
                        (has_ip and 'hpt' in ab_ipc_options),
                        (has_ip and 'ipt' in ab_ipc_options),
                        (has_lp and 'lpt' in ab_ipc_options),
                     has_lp,
                        (has_lp and 'atmos' in ab_lpc_options),
                        (has_lp and 'hpt' in ab_lpc_options),
                        (has_lp and 'ipt' in ab_lpc_options),
                        (has_lp and 'lpt' in ab_lpc_options),
                    ]

        # Group the decisions
        decisions_inter = [include_eb_hb_options, include_eb_ih_options, include_eb_li_options]
        decisions_intra = [include_ab_hpc_options, include_ab_ipc_options, include_ab_lpc_options]

        # Group the targets
        targets_inter = [eb_hb_options, eb_ih_options, eb_li_options]
        targets_intra = [ab_hpc_options, ab_ipc_options, ab_lpc_options]

        # Group the bleed fractions
        fractions_inter = [[eb_hba_frac_w, eb_hbh_frac_w, eb_hbi_frac_w, eb_hbl_frac_w],
                           [eb_iha_frac_w, eb_ihh_frac_w, eb_ihi_frac_w, eb_ihl_frac_w],
                           [eb_lia_frac_w, eb_lih_frac_w, eb_lii_frac_w, eb_lil_frac_w]]
        fractions_intra = [[ab_ha_frac_w, ab_hh_frac_w, ab_hi_frac_w, ab_hl_frac_w],
                           [ab_ia_frac_w, ab_ih_frac_w, ab_ii_frac_w, ab_il_frac_w],
                           [ab_la_frac_w, ab_lh_frac_w, ab_li_frac_w, ab_ll_frac_w]]

        # Add the inter-bleed
        for shafts, decision in enumerate(decisions_inter):
            if decision != 0 and turbines-1 >= shafts:
                self._include_bleed_inter(architecture, targets_inter[shafts], fractions_inter[shafts], shafts)

        # Add the intra-bleed
        for shafts, decision in enumerate(decisions_intra):
            if decision != 0 and turbines-1 >= shafts:
                self._include_bleed_intra(architecture, targets_intra[shafts], fractions_intra[shafts], shafts)

        return is_active

    @staticmethod
    def _include_bleed_inter(architecture: TurbofanArchitecture, targets: list, fractions: list, number: int):

        # Find compressors, burner and turbines
        compressors = architecture.get_elements_by_type(Compressor)
        burner = architecture.get_elements_by_type(Burner)[0]
        turbines = architecture.get_elements_by_type(Turbine)

        # Create inter-bleed name
        name = 'bld_inter_' + str(number)

        # Specify targets bleed
        adjusted_targets = []
        adjusted_fractions = []
        bleed_names = []
        if 'atmos' in targets:
            adjusted_targets.append('atmos')
            adjusted_fractions.append(fractions[targets.index('atmos')])
            bleed_names.append(name + '_atmos')
        if 'hpt' in targets:
            adjusted_targets.append('turbine')
            adjusted_fractions.append(fractions[targets.index('hpt')])
            bleed_names.append(name + '_turbine')
            turbines[0].bleed_names.append(name + '_turbine')
        if 'ipt' in targets and len(turbines) >= 2:
            adjusted_targets.append('turb_ip')
            adjusted_fractions.append(fractions[targets.index('ipt')])
            bleed_names.append(name + '_turb_ip')
            turbines[1].bleed_names.append(name + '_turb_ip')
        if 'lpt' in targets and len(turbines) == 3:
            adjusted_targets.append('turb_lp')
            adjusted_fractions.append(fractions[targets.index('lpt')])
            bleed_names.append(name + '_turb_lp')
            turbines[2].bleed_names.append(name + '_turb_lp')

        # Specify targets bleed-inter component
        target = compressors[-1*number] if number > 0 else burner

        # Create new element(s): BleedInter
        bleed_inter = BleedInter(
            name=name, target=target, target_bleed=adjusted_targets,
            bleed_names=bleed_names, source_frac_w=adjusted_fractions
        )

        # Reroute flows
        compressors[-1-1*number].target = bleed_inter

        # Add BleedInter to architecture elements
        architecture.elements.insert(architecture.elements.index(compressors[-1-1*number])+1, bleed_inter)

    @staticmethod
    def _include_bleed_intra(architecture: TurbofanArchitecture, targets: list, fractions: list, number: int):

        # Find compressors and turbines
        compressors = architecture.get_elements_by_type(Compressor)
        turbines = architecture.get_elements_by_type(Turbine)

        # Create intra-bleed name
        name = 'bld_intra_' + str(number)

        # Specify sources bleed-intra component
        source = compressors[-1-1*number]
        source_name = '_hpc' if number == 0 else ('_ipc' if number == 1 else '_lpc')

        # Specify targets bleed
        adjusted_targets = []
        adjusted_fractions = []
        bleed_names = []
        if 'atmos' in targets:
            adjusted_targets.append('atmos')
            adjusted_fractions.append(fractions[targets.index('atmos')])
            bleed_names.append(name + source_name + '_atmos')
            compressors[-1-1*number].bleed_names.append(name + source_name + '_atmos')
        if 'hpt' in targets:
            adjusted_targets.append('turbine')
            adjusted_fractions.append(fractions[targets.index('hpt')])
            bleed_names.append(name + source_name + '_hp')
            compressors[-1-1*number].bleed_names.append(name + source_name + '_hp')
            turbines[0].bleed_names.append(name + source_name + '_hp')
        if 'ipt' in targets and len(turbines) >= 2:
            adjusted_targets.append('turb_ip')
            adjusted_fractions.append(fractions[targets.index('ipt')])
            bleed_names.append(name + source_name + '_ip')
            compressors[-1-1*number].bleed_names.append(name + source_name + '_ip')
            turbines[1].bleed_names.append(name + source_name + '_ip')
        if 'lpt' in targets and len(turbines) == 3:
            adjusted_targets.append('turb_lp')
            adjusted_fractions.append(fractions[targets.index('lpt')])
            bleed_names.append(name + source_name + '_lp')
            compressors[-1-1*number].bleed_names.append(name + source_name + '_lp')
            turbines[2].bleed_names.append(name + source_name + '_lp')

        # Create new element(s): BleedIntra
        bleed_intra = BleedIntra(
            name=name, source=source, target=adjusted_targets,
            bleed_names=bleed_names, source_frac_w=adjusted_fractions
        )

        # Add BleedInter to architecture elements
        architecture.elements.insert(architecture.elements.index(compressors[-1-1*number])+1, bleed_intra)
