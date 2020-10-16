import openmdao.api as om
import pycycle.api as pyc
from open_turb_arch.architecture.flow import *
import open_turb_arch.architecture.units as units
from open_turb_arch.architecture.turbomachinery import *
from open_turb_arch.architecture import TurbofanArchitecture
from open_turb_arch.analysis.builder import ArchitectureCycle, ArchitectureMultiPointCycle, Balancer

__all__ = ['Balancer', 'DesignBalancer', 'OffDesignBalancer']


class DesignBalancer(Balancer):
    """
    Balancer for the design point:
    - Uses inlet mass flow rate to tune the required thrust
    - Uses burner fuel-to-air ratio to tune the turbine inlet temperature
    - Uses turbine pressure ratio to balance shaft net power (should be 0)
    """

    def __init__(
            self,
            init_mass_flow: float = 80.,  # kg/s
            init_far: float = .017,
            init_turbine_pr: float = 2.,
    ):
        self._init_mass_flow = init_mass_flow
        self._init_far = init_far
        self._init_turbine_pr = init_turbine_pr

    def apply(self, cycle: ArchitectureCycle, architecture: TurbofanArchitecture):
        balance = cycle.add_subsystem(self.balance_name, om.BalanceComp())

        self._balance_thrust(cycle, balance)
        self._balance_turbine_temp(cycle, balance)
        self._balance_shaft_power(cycle, balance, architecture)

    def connect_des_od(self, mp_cycle: ArchitectureMultiPointCycle, architecture: TurbofanArchitecture):
        pass

    def _balance_thrust(self, cycle: ArchitectureCycle, balance: om.BalanceComp):
        # Add a balance for W (engine mass flow rate)
        balance.add_balance('W', units=units.MASS_FLOW, eq_units='lbf', val=self._init_mass_flow, rhs_name='Fn_target')

        # Use the balance parameter to control the inlet mass flow rate (to size the area)
        cycle.connect(balance.name +'.W', cycle.inlet_el_name + '.Fl_I:stat:W')

        # To force the overall net thrust equal to Fn_target (rhs name; assigned in OperatingCondition.set_values)
        cycle.connect('perf.Fn', balance.name+'.lhs:W')

    def _balance_turbine_temp(self, cycle: ArchitectureCycle, balance: om.BalanceComp):
        burners = cycle.get_element_names(pyc.Combustor, prefix_cycle_name=False)
        if len(burners) == 0:
            return
        if len(burners) > 1:
            raise RuntimeError('Currently only one burner supported for T4 balancing')

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


class OffDesignBalancer(Balancer):
    """
    Balancer for the off-design points:
    - Uses burner fuel-to-air ratio to tune the required thrust
    - Uses inlet mass flow rate to sync inlet area with design point
    - Uses splitter BPR to sync bypass nozzle area with design point
    - Uses shaft rpm to balance shaft net power (should be 0)
    """

    def __init__(
            self,
            init_mass_flow = 90.,  # kg/s
            init_bpr = 5.,
            init_far = .017,
            init_shaft_rpm = 5000.,  # rpm
    ):
        self._init_mass_flow = init_mass_flow
        self._init_bpr = init_bpr
        self._init_far = init_far
        self._init_shaft_rpm = init_shaft_rpm

    def apply(self, cycle: ArchitectureCycle, architecture: TurbofanArchitecture):
        balance = cycle.add_subsystem(self.balance_name, om.BalanceComp())

        self._balance_thrust(cycle, balance)
        self._balance_areas(cycle, balance, architecture)
        self._balance_shaft_power(cycle, balance, architecture)

    def connect_des_od(self, mp_cycle: ArchitectureMultiPointCycle, architecture: TurbofanArchitecture):
        self._connect_balance_des_od(mp_cycle, architecture)

    def _balance_thrust(self, cycle: ArchitectureCycle, balance: om.BalanceComp):
        burners = cycle.get_element_names(pyc.Combustor, prefix_cycle_name=False)
        if len(burners) == 0:
            return
        if len(burners) > 1:
            raise RuntimeError('Currently only one burner supported for off-design T4 balancing')

        # Add a balance for FAR (fuel-to-air ratio)
        balance.add_balance('FAR', eq_units='lbf', lower=1e-4, val=self._init_far, rhs_name='Fn_target')

        # Use the balance to control the burner fuel-to-air ratio
        cycle.connect(balance.name+'.FAR', burners[0]+'.Fl_I:FAR')

        # To force the overall net thrust equal to Fn_target (rhs name; assigned in OperatingCondition.set_values)
        cycle.connect('perf.Fn', balance.name+'.lhs:FAR')

    @staticmethod
    def _iter_nozzle_balances(architecture: TurbofanArchitecture):
        nozzle_names = [el.name for el in architecture.elements if isinstance(el, Nozzle)]
        inlet_names = [el.name for el in architecture.elements if isinstance(el, Inlet)]
        splitter_names = [el.name for el in architecture.elements if isinstance(el, Splitter)]

        if len(inlet_names)+len(splitter_names) != len(nozzle_names):
            raise RuntimeError('Number of inlets + number of splitters should be same as number of nozzles')

        for i, (is_inlet, el_name) in enumerate([(True, name) for name in inlet_names]+
                                                [(False, name) for name in splitter_names]):
            base_name = 'W' if is_inlet else 'BPR'
            param_name = '%s_%d' % (base_name, i)

            yield is_inlet, el_name, nozzle_names[i], param_name

    def _balance_areas(self, cycle: ArchitectureCycle, balance: om.BalanceComp, architecture: TurbofanArchitecture):
        """
        Areas are balanced by making sure mass flows are correct. Assumptions:
        - There is 1 inlet
        - For every additional (>1) nozzle, there is a splitter (after the inlet)
        - Number of inlets + number of splitters = number of nozzles

        NOTE: this therefore does not work if there are any flow mixers!
        """
        for is_inlet, el_name, nozzle_name, param_name in self._iter_nozzle_balances(architecture):
            if is_inlet:
                # Add a balance for W (mass flow rate)
                balance.add_balance(param_name, units=units.MASS_FLOW, eq_units='inch**2', lower=5., upper=500.,
                                    val=self._init_mass_flow)

                # Use the balance parameter to control the inlet mass flow rate
                cycle.connect('%s.%s' % (balance.name, param_name), el_name+'.Fl_I:stat:W')

            else:
                # Add a balance for BPR (bypass ratio)
                balance.add_balance(param_name, val=self._init_bpr, lower=1., upper=30., eq_units='inch**2')

                # Use the balance parameter to control the splitter bypass ratio
                cycle.connect('%s.%s' % (balance.name, param_name), el_name+'.BPR')

            # To force the nozzle area equal to the design point
            cycle.connect(nozzle_name+'.Throat:stat:area', '%s.lhs:%s' % (balance.name, param_name))

    def _connect_balance_des_od(self, mp_cycle: ArchitectureMultiPointCycle, architecture: TurbofanArchitecture):
        connect_key = 'nozzle_area'
        if connect_key in mp_cycle.balance_connected_des_od:
            return
        mp_cycle.balance_connected_des_od.add(connect_key)

        for _, _, nozzle_name, param_name in self._iter_nozzle_balances(architecture):
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
