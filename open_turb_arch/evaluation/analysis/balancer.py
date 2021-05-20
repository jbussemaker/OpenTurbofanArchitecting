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

import openmdao.api as om
import warnings
import pycycle.api as pyc
from open_turb_arch.evaluation.architecture.flow import *
import open_turb_arch.evaluation.architecture.units as units
from open_turb_arch.evaluation.architecture.turbomachinery import *
from open_turb_arch.evaluation.architecture import TurbofanArchitecture
from open_turb_arch.evaluation.analysis.builder import ArchitectureCycle, ArchitectureMultiPointCycle, Balancer

__all__ = ['Balancer', 'DesignBalancer', 'OffDesignBalancer']


class DesignBalancer(Balancer):
    """
    Balancer for the design point:
    - Uses inlet mass flow rate to tune the required thrust
    - Uses compressor bleed fraction to tune the extraction bleed
    - Uses burner fuel-to-air ratio to tune the turbine inlet temperature
    - Uses turbine pressure ratio to balance shaft net power (should be 0)
    """

    def __init__(
            self,
            init_mass_flow: float = 80.,  # kg/s
            init_far: float = .017,
            init_turbine_pr: float = 2.,
            init_extraction_bleed_frac: float = 0.02,
            init_gearbox_torque: float = 32500,
            init_mixer_er: float = 5.,
    ):
        self._init_mass_flow = init_mass_flow
        self._init_far = init_far
        self._init_turbine_pr = init_turbine_pr
        self._init_extraction_bleed_frac = init_extraction_bleed_frac
        self._init_gearbox_torque = init_gearbox_torque
        self._init_mixer_er = init_mixer_er

    def apply(self, cycle: ArchitectureCycle, architecture: TurbofanArchitecture):
        balance = cycle.add_subsystem(self.balance_name, om.BalanceComp())

        self._balance_thrust(cycle, balance)
        self._balance_extraction_bleed(cycle, balance, architecture)
        self._balance_turbine_temp(cycle, balance)
        self._balance_shaft_power(cycle, balance, architecture)
        self._balance_gearbox(cycle, balance, architecture)
        self._balance_mixer(cycle, balance, architecture)

    def connect_des_od(self, mp_cycle: ArchitectureMultiPointCycle, architecture: TurbofanArchitecture):
        pass

    def _balance_thrust(self, cycle: ArchitectureCycle, balance: om.BalanceComp):
        # Add a balance for W (engine mass flow rate)
        balance.add_balance('W', units=units.MASS_FLOW, eq_units='lbf', val=self._init_mass_flow, rhs_name='Fn_target')

        # Use the balance parameter to control the inlet mass flow rate (to size the area)
        cycle.connect(balance.name+'.W', cycle.inlet_el_name+'.Fl_I:stat:W')

        # To force the overall net thrust equal to Fn_target (rhs name; assigned in OperatingCondition.set_values)
        cycle.connect('perf.Fn', balance.name+'.lhs:W')

    def _balance_extraction_bleed(self, cycle: ArchitectureCycle, balance: om.BalanceComp, architecture: TurbofanArchitecture):
        # Add a balance for extraction bleed
        balance.add_balance('extraction_bleed', eq_units='lbm/s', val=self._init_extraction_bleed_frac, rhs_name='extraction_bleed_target')

        # Extraction bleed is only active for the selected compressor
        for compressor in architecture.get_elements_by_type(Compressor):
            if compressor.offtake_bleed:
                # Use the balance parameter to control the extraction bleed fraction from the compressor
                cycle.connect(balance.name+'.extraction_bleed', compressor.name+'.bleed_offtake_atmos:frac_W')
                # To force the extraction bleed fraction equal to bleed_target (rhs name; assigned in DesignCondition.set_values)
                cycle.connect(compressor.name+'.bleed_offtake_atmos:stat:W', balance.name+'.lhs:extraction_bleed')

    def _balance_turbine_temp(self, cycle: ArchitectureCycle, balance: om.BalanceComp):
        burners = cycle.get_element_names(pyc.Combustor, prefix_cycle_name=False)

        # Add a balance for FAR (fuel-to-air ratio)
        balance.add_balance('FAR', eq_units='degR', lower=1e-4, val=self._init_far, rhs_name='T4_target')

        # Use the balance parameter to control the burner fuel-to-air ratio
        cycle.connect(balance.name+'.FAR', burners[0]+'.Fl_I:FAR')

        # To force the turbine inlet temperature equal to T4_target (rhs name; assigned in DesignCondition.set_values)
        cycle.connect(burners[0]+'.Fl_O:tot:T', balance.name+'.lhs:FAR')

    def _balance_shaft_power(self, cycle: ArchitectureCycle, balance: om.BalanceComp,
                             architecture: TurbofanArchitecture):
        # Loop over turbines
        for turbine in architecture.elements:
            if not isinstance(turbine, Turbine):
                continue
            shaft = turbine.shaft

            # Add a balance for the turbine pressure ratio
            param_name = turbine.name+'_PR'
            balance.add_balance(param_name, val=self._init_turbine_pr, lower=1.001, upper=15, eq_units='hp', rhs_val=0.)

            # Use the balance parameter to control the turbine pressure ratio
            cycle.connect('%s.%s' % (balance.name, param_name), turbine.name+'.PR')

            # To force the shaft net power to zero (out power equal to in power)
            cycle.connect(shaft.name+'.pwr_net', '%s.lhs:%s' % (balance.name, param_name))

    def _balance_gearbox(self, cycle: ArchitectureCycle, balance: om.BalanceComp,
                         architecture: TurbofanArchitecture):
        if len(architecture.get_elements_by_type(Gearbox)):
            balance.add_balance('gb_trq', val=self._init_gearbox_torque, units=units.TORQUE, eq_units='hp', rhs_val=0.)
            cycle.connect(balance.name+'.gb_trq', 'gearbox.trq_base')
            cycle.connect('fan_shaft.pwr_net', balance.name+'.lhs:gb_trq')
        else:
            pass

    def _balance_mixer(self, cycle: ArchitectureCycle, balance: om.BalanceComp,
                       architecture: TurbofanArchitecture):
        if len(architecture.get_elements_by_type(Mixer)):
            balance.add_balance('BPR', val=self._init_mixer_er, eq_units=None, lower=1e-4)
            cycle.connect(balance.name+'.BPR', 'splitter.BPR')
            cycle.connect('mixer.ER', balance.name+'.lhs:BPR')
        else:
            pass


class OffDesignBalancer(Balancer):
    """
    Balancer for the off-design points:
    - Uses burner fuel-to-air ratio to tune the required thrust
    - Uses compressor bleed fraction to tune the extraction bleed
    - Uses inlet mass flow rate to sync inlet area with design point
    - Uses splitter BPR to sync bypass nozzle area with design point
    - Uses shaft rpm to balance shaft net power (should be 0)
    """

    def __init__(
            self,
            init_mass_flow: float = 90.,  # kg/s
            init_bpr: float = 5.,
            init_far: float = .017,
            init_shaft_rpm: float = 5000.,  # rpm
            init_extraction_bleed_frac: float = 0.02,
    ):
        self._init_mass_flow = init_mass_flow
        self._init_bpr = init_bpr
        self._init_far = init_far
        self._init_shaft_rpm = init_shaft_rpm
        self._init_extraction_bleed_frac = init_extraction_bleed_frac

    def apply(self, cycle: ArchitectureCycle, architecture: TurbofanArchitecture):
        balance = cycle.add_subsystem(self.balance_name, om.BalanceComp())

        self._balance_thrust(cycle, balance)
        self._balance_extraction_bleed(cycle, balance, architecture)
        self._balance_areas(cycle, balance, architecture)
        self._balance_shaft_power(cycle, balance, architecture)

        # Execute balancer before all other elements
        names = [el.name for el in cycle.pyc_elements]
        cycle.set_order([self.balance_name]+names)

    def connect_des_od(self, mp_cycle: ArchitectureMultiPointCycle, architecture: TurbofanArchitecture):
        self._connect_balance_des_od(mp_cycle, architecture)

    def _balance_thrust(self, cycle: ArchitectureCycle, balance: om.BalanceComp):
        burners = cycle.get_element_names(pyc.Combustor, prefix_cycle_name=False)

        # Add a balance for FAR (fuel-to-air ratio)
        balance.add_balance('FAR', eq_units='lbf', lower=1e-4, val=self._init_far, rhs_name='Fn_target')

        # Use the balance to control the burner fuel-to-air ratio
        cycle.connect(balance.name+'.FAR', burners[0]+'.Fl_I:FAR')

        # To force the overall net thrust equal to Fn_target (rhs name; assigned in OperatingCondition.set_values)
        cycle.connect('perf.Fn', balance.name+'.lhs:FAR')

    def _balance_extraction_bleed(self, cycle: ArchitectureCycle, balance: om.BalanceComp, architecture: TurbofanArchitecture):
        # Add a balance for extraction bleed
        balance.add_balance('extraction_bleed', eq_units='lbm/s', val=self._init_extraction_bleed_frac, rhs_name='extraction_bleed_target')

        # Extraction bleed is only active for the selected compressor
        for compressor in architecture.get_elements_by_type(Compressor):
            if compressor.offtake_bleed:
                # Use the balance parameter to control the extraction bleed fraction from the compressor
                cycle.connect(balance.name+'.extraction_bleed', compressor.name+'.bleed_offtake_atmos:frac_W')
                # To force the extraction bleed fraction equal to bleed_target (rhs name; assigned in DesignCondition.set_values)
                cycle.connect(compressor.name+'.bleed_offtake_atmos:stat:W', balance.name+'.lhs:extraction_bleed')

    @staticmethod
    def _iter_nozzle_balances(architecture: TurbofanArchitecture):
        nozzle_names = [el.name for el in architecture.elements if isinstance(el, Nozzle)]
        inlet_names = [el.name for el in architecture.elements if isinstance(el, Inlet)]
        splitter_names = [el.name for el in architecture.elements if isinstance(el, Splitter)]
        mixer_names = [el.name for el in architecture.elements if isinstance(el, Mixer)]

        if len(inlet_names)+len(splitter_names)+len(mixer_names) != len(nozzle_names):
            raise RuntimeError('Number of inlets + number of splitters + number of mixers should be same as number of nozzles')

        for i, (component, el_name) in enumerate([('inlet', name) for name in inlet_names]+
                                                 [('splitter', name) for name in splitter_names]+
                                                 [('mixer', name) for name in mixer_names]):
            base_name = 'W' if component == 'inlet' else ('BPR' if component == 'splitter' else 'ER')
            param_name = '%s_%d' % (base_name, i)

            yield component, el_name, nozzle_names[i], param_name

    def _balance_areas(self, cycle: ArchitectureCycle, balance: om.BalanceComp, architecture: TurbofanArchitecture):
        """
        Areas are balanced by making sure mass flows are correct. Assumptions:
        - There is 1 inlet
        - For every additional (>1) nozzle, there is a splitter (after the inlet)
        - For every mixer, there is an additional nozzle (after the inlet)
        - Number of inlets + number of splitters + number of mixers = number of nozzles
        """
        for component, el_name, nozzle_name, param_name in self._iter_nozzle_balances(architecture):
            if component == 'inlet':
                # Add a balance for W (mass flow rate)
                balance.add_balance(param_name, units=units.MASS_FLOW, eq_units='inch**2', lower=5., upper=500.,
                                    val=self._init_mass_flow)

                # Use the balance parameter to control the inlet mass flow rate
                cycle.connect('%s.%s' % (balance.name, param_name), el_name+'.Fl_I:stat:W')

            elif component == 'splitter':
                # Add a balance for BPR (bypass ratio)
                balance.add_balance(param_name, val=self._init_bpr, lower=1., upper=30., eq_units='inch**2')

                # Use the balance parameter to control the splitter bypass ratio
                cycle.connect('%s.%s' % (balance.name, param_name), el_name+'.BPR')

            # To force the nozzle area equal to the design point
            if component != 'mixer':
                cycle.connect(nozzle_name+'.Throat:stat:area', '%s.lhs:%s' % (balance.name, param_name))

    def _connect_balance_des_od(self, mp_cycle: ArchitectureMultiPointCycle, architecture: TurbofanArchitecture):
        connect_key = 'nozzle_area'
        if connect_key in mp_cycle.balance_connected_des_od:
            return
        mp_cycle.balance_connected_des_od.add(connect_key)

        for component, _, nozzle_name, param_name in self._iter_nozzle_balances(architecture):
            if component != 'mixer':
                mp_cycle.pyc_connect_des_od(nozzle_name+'.Throat:stat:area', '%s.rhs:%s' % (self.balance_name, param_name))

    def _balance_shaft_power(self, cycle: ArchitectureCycle, balance: om.BalanceComp,
                             architecture: TurbofanArchitecture):
        # Loop over shafts
        for shaft in architecture.elements:
            if not isinstance(shaft, Shaft):
                continue

            # Add a balance for shaft rpm
            param_name = shaft.name+'_Nmech'
            balance.add_balance(param_name, val=self._init_shaft_rpm, units=units.RPM, lower=500., eq_units='hp',
                                rhs_val=0.)

            # Use the balance parameter to control the shaft rpm
            cycle.connect('%s.%s' % (balance.name, param_name), shaft.name+'_Nmech')  # Promoted name

            # To force the shaft net power to zero (out power equal to in power)
            cycle.connect(shaft.name+'.pwr_net', '%s.lhs:%s' % (balance.name, param_name))
