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

import sys
import warnings
import numpy as np
from typing import *
import openmdao.api as om
import pycycle.api as pyc
from ordered_set import OrderedSet
from dataclasses import dataclass, field
import open_turb_arch.evaluation.architecture.units as units
from open_turb_arch.evaluation.architecture.turbomachinery import *
from open_turb_arch.evaluation.architecture.flow import *
from open_turb_arch.evaluation.architecture.architecture import *
from open_turb_arch.evaluation.analysis.disciplines import *

__all__ = ['CycleBuilder', 'ArchitectureCycle', 'ArchitectureMultiPointCycle', 'OperatingCondition', 'DesignCondition',
           'EvaluateCondition', 'OperatingMetrics', 'AnalysisProblem']


@dataclass(frozen=False)
class OperatingCondition:
    """Describes the operating conditions a turbofan architecture will be evaluated at."""

    mach: float  # Mach number
    alt: float  # Altitude [ft]
    thrust: float  # Required thrust [N]
    balancer: 'Balancer' = None

    d_temp: float = 0.  # Difference to ISA temperature [C]
    bleed_offtake: float = 0.  # Bleed air offtake [kg/s]
    power_offtake: float = 0.  # Shaft power offtake [W]

    @property
    def name(self):
        return self._get_name()

    def _get_name(self) -> str:
        raise NotImplementedError

    def set_values(self, problem: om.Problem):
        problem.set_val(self.name+'.fc.MN', self.mach)
        problem.set_val(self.name+'.fc.alt', self.alt, units=units.ALTITUDE)
        problem.set_val('%s.%s.Fn_target' % (self.name, self.balancer.balance_name), self.thrust, units=units.FORCE)

        try:
            problem.set_val('%s.%s.extraction_bleed_target' % (self.name, self.balancer.balance_name), self.bleed_offtake, units=units.MASS_FLOW)
        except KeyError:
            pass  # Happens when no extraction bleed is added

        if self.d_temp != 0:
            problem.set_val(self.name+'.fc.dTs', self.d_temp, units=units.TEMPERATURE)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return id(self)


@dataclass(frozen=False)
class DesignCondition(OperatingCondition):
    turbine_in_temp: float = 0.  # Turbine inlet temperature [C]

    def set_values(self, problem: om.Problem):
        super(DesignCondition, self).set_values(problem)

        if self.turbine_in_temp == 0.:
            raise ValueError('Must set a target turbine inlet temperature for the design condition')
        problem.set_val('%s.%s.T4_target' % (self.name, self.balancer.balance_name), self.turbine_in_temp, units=units.TEMPERATURE)

    def _get_name(self) -> str:
        return 'design'

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return id(self)


@dataclass(frozen=False)
class EvaluateCondition(OperatingCondition):
    """pyCycle: off-design condition"""
    name_: str = None

    def _get_name(self) -> str:
        if self.name_ is None:
            raise ValueError('Must provide a name to an evaluation condition')
        return self.name_

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return id(self)


@dataclass(frozen=False)
class AnalysisProblem:
    """Defines how the turbofan architectures will be analyzed."""

    design_condition: DesignCondition
    evaluate_conditions: List[EvaluateCondition] = field(default_factory=list)


@dataclass(frozen=False)
class OperatingMetrics:
    """A container for analysis results for a given operating condition."""

    fuel_flow: float = None  # Fuel usage [kg/s]
    mass_flow: float = None  # Engine air mass flow [kg/s]
    thrust: float = None  # Net thrust generated [N]
    tsfc: float = None  # Thrust Specific Fuel Consumption [g/kN s]
    opr: float = None  # Overall pressure ratio
    area_inlet: float = None  # Engine inlet area [m2]
    area_jet: float = None  # Outlet area of the jet nozzle [m2]
    v_jet: float = None  # Outlet velocity of the jet nozzle [m/s]
    mach_jet: float = None  # Outlet mach number of the jet nozzle
    p_atm: float = None  # Atmospheric pressure [Pa]
    t_atm: float = None  # Atmospheric temperature [degC]
    p_burner_in: float = None  # Burner inlet pressure [Pa]
    t_burner_in: float = None  # Burner inlet temperature [degC]
    p_itb_in: float = None  # Inter-turbine burner inlet pressure [Pa]
    t_itb_in: float = None  # Inter-turbine burner inlet temperature [degC]
    p_ab_in: float = None  # Afterburner inlet pressure [Pa]
    t_ab_in: float = None  # Afterburner inlet temperature [degC]
    p_jet: float = None  # Jet nozzle exit pressure [Pa]
    t_jet: float = None  # Jet nozzle exit temperature [degC]


class ArchitectureCycle(pyc.Cycle):
    """A cycle evaluating the architecture for a specific operating condition."""

    def __init__(self, architecture: TurbofanArchitecture, condition: OperatingCondition, max_iter=20):
        design = isinstance(condition, DesignCondition)
        super(ArchitectureCycle, self).__init__(design=design)

        self.architecture: TurbofanArchitecture = architecture
        self.condition: OperatingCondition = condition
        self._max_iter = max_iter

        self._elements = OrderedSet()

    def initialize(self):
        self.options.declare('design', default=True,
                             desc='Switch between on-design and off-design calculation.')

    @property
    def is_design_condition(self):
        return isinstance(self.condition, DesignCondition)

    @property
    def inlet_el_name(self):
        for el in self._elements:
            if isinstance(el, pyc.Inlet):
                return el.name
        raise RuntimeError('No inlet defined in cycle')

    @property
    def pyc_elements(self):
        yield from self._elements

    def setup(self):
        design = self.is_design_condition
        thermo_data = pyc.species_data.janaf

        self._add_flight_conditions(thermo_data)
        for element in self.architecture.elements:
            element.add_element_prepare(self, thermo_data, design)
        for element in self.architecture.elements:
            element.add_element(self, thermo_data, design)
        self._add_performance()

        for element in self.architecture.elements:
            element.connect(self)
        self._connect_performance()

        self._add_balance()

        self._set_solvers()

    def _add_flight_conditions(self, thermo_data):
        self.pyc_add_element('fc', pyc.FlightConditions(thermo_data=thermo_data, elements=pyc.AIR_ELEMENTS))

    def _add_performance(self):
        n_nozzles = 0
        n_burners = 0
        for pyc_element in self._elements:
            if isinstance(pyc_element, pyc.Nozzle):
                n_nozzles += 1
            elif isinstance(pyc_element, pyc.Combustor):
                n_burners += 1

        self.pyc_add_element('perf', pyc.Performance(num_nozzles=n_nozzles, num_burners=n_burners))

    def _connect_performance(self):
        i_nozzle = 0
        i_burner = 0
        for pyc_el in self._elements:
            if isinstance(pyc_el, pyc.Nozzle):  # Nozzle gross thrust
                self.connect(pyc_el.name+'.Fg', 'perf.Fg_%d' % i_nozzle)
                i_nozzle += 1

            elif isinstance(pyc_el, pyc.Combustor):  # Combustor fuel flow and inflow total pressure
                self.connect(pyc_el.name+'.Wfuel', 'perf.Wfuel_%d' % i_burner)

                if i_burner == 0:
                    # Find out where the burner receives its flow from
                    target_conn_name = pyc_el.name+'.Fl_I:tot:P'
                    for manual_connections in [self._manual_connections, self._static_manual_connections]:
                        if target_conn_name in manual_connections:
                            src_name = manual_connections[target_conn_name][0]
                            break
                    else:
                        raise RuntimeError('Burner has no incoming flow: %r' % pyc_el.name)
                    src_el_name = src_name.split('.')[0]

                    self.connect(src_el_name+('.Fl_O:tot:P' if src_el_name != 'intercooler' else '.Fl_O1:tot:P'), 'perf.Pt3')

                i_burner += 1

            elif isinstance(pyc_el, pyc.Inlet):  # Inlet ram drag and outflow total pressure
                self.connect(pyc_el.name+'.F_ram', 'perf.ram_drag')
                self.connect(pyc_el.name+'.Fl_O:tot:P', 'perf.Pt2')

    def _add_balance(self):
        self.condition.balancer.apply(self, self.architecture)

    def _set_solvers(self):
        newton = self.nonlinear_solver = om.NewtonSolver()
        newton.options['atol'] = 1e-8
        newton.options['rtol'] = 1e-8
        newton.options['iprint'] = 2
        newton.options['maxiter'] = self._max_iter
        newton.options['solve_subsystems'] = True
        newton.options['max_sub_solves'] = 100
        newton.options['reraise_child_analysiserror'] = False
        newton.options['err_on_non_converge'] = True

        ls = newton.linesearch = om.ArmijoGoldsteinLS()
        ls.options['maxiter'] = 3
        ls.options['bound_enforcement'] = 'scalar'

        self.linear_solver = om.DirectSolver(assemble_jac=True)

    def print_results(self, problem: om.Problem, fp=sys.stdout):
        self._print_performance(problem, fp=fp)
        self._print_disciplines(problem, fp=fp)

        flow_stations = ['%s.fc.Fl_O' % self.name]
        massflow_inlet = problem.get_val('%s.inlet.Fl_O:stat:W' % self.name, get_remote=None),
        problem.set_val(self.name+'.fc.Fl_O:stat:W', massflow_inlet)
        element: om.Group
        sub_sys: om.Group
        for element in self._elements:
            processed_flows = set()
            for output_param in element.abs_name_iter('output'):
                if 'Fl_O' in output_param and ':tot:P' in output_param and 'b4bld' not in output_param:
                    flow_name = output_param.split(':')[0].split('.')[-1]
                    if flow_name not in processed_flows:
                        processed_flows.add(flow_name)
                        abs_flow_name = '%s.%s.%s' % (self.name, element.name, flow_name)
                        if abs_flow_name not in flow_stations:
                            flow_stations.append(abs_flow_name)
        pyc.print_flow_station(problem, flow_stations, file=fp)

        pyc.print_compressor(problem, self.get_element_names(pyc.Compressor), file=fp)

        pyc.print_burner(problem, self.get_element_names(pyc.Combustor), file=fp)

        pyc.print_turbine(problem, self.get_element_names(pyc.Turbine), file=fp)

        pyc.print_nozzle(problem, self.get_element_names(pyc.Nozzle), file=fp)

        pyc.print_shaft(problem, self.get_element_names(pyc.Shaft), file=fp)

        gearbox_names = self.get_element_names(pyc.Gearbox)
        if len(gearbox_names) > 0:
            pyc.print_gearbox(problem, gearbox_names, file=fp)

        heatexchanger_names = self.get_element_names(pyc.HeatExchanger)
        if len(heatexchanger_names) > 0:
            pyc.print_heatexchanger(problem, heatexchanger_names, file=fp)

        mixer_names = self.get_element_names(pyc.Mixer)
        if len(mixer_names) > 0:
            pyc.print_mixer(problem, mixer_names, file=fp)

        bleed_names = self.get_element_names(pyc.BleedOut)+self.get_element_names(pyc.Compressor)
        if len(bleed_names) > 0:
            pyc.print_bleed(problem, bleed_names, file=fp)

    def get_element_names(self, el_type: Type[om.Group], prefix_cycle_name=True) -> List[str]:
        return ['%s.%s' % (self.name, el.name) if prefix_cycle_name else el.name
                for el in self._elements if isinstance(el, el_type)]

    def _print_performance(self, problem: om.Problem, fp=sys.stdout):
        inlet = self.inlet_el_name
        data = (
            problem[self.name+'.fc.Fl_O:stat:MN'],
            problem.get_val(self.name+'.fc.alt', units=units.ALTITUDE, get_remote=None),
            problem.get_val('%s.%s.Fl_O:stat:W' % (self.name, inlet), units=units.MASS_FLOW, get_remote=None),
            problem.get_val(self.name+'.perf.Fn', units=units.FORCE, get_remote=None),
            problem.get_val(self.name+'.perf.Fg', units=units.FORCE, get_remote=None),
            problem.get_val('%s.%s.F_ram' % (self.name, inlet), units=units.FORCE, get_remote=None),
            problem[self.name+'.perf.OPR'],
            problem.get_val(self.name+'.perf.TSFC', units=units.TSFC, get_remote=None),
        )

        for _ in range(3):
            print(file=fp, flush=True)
        print("----------------------------------------------------------------------------", file=fp, flush=True)
        print("                              POINT:", self.name, file=fp, flush=True)
        print("----------------------------------------------------------------------------", file=fp, flush=True)
        print("                       PERFORMANCE CHARACTERISTICS", file=fp, flush=True)
        print("    Mach      Alt       W      Fn      Fg    Fram     OPR     TSFC  ", file=fp, flush=True)
        print("    [-]       [ft]    [kg/s]   [N]     [N]   [-]      [-]    [g/kNs]  ", file=fp, flush=True)
        print(" %7.5f  %7.1f %7.3f %7.1f %7.1f %7.1f %7.3f  %7.5f" % data, file=fp, flush=True)

    def _print_disciplines(self, problem: om.Problem, fp=sys.stdout):
        data = (
            Weight(self.get_metrics(problem), self.architecture).weight_calculation()[0],
            Length(self.get_metrics(problem), self.architecture).length_calculation()[0],
            Diameter(self.get_metrics(problem), self.architecture).diameter_calculation()[1],
            NOx(self.get_metrics(problem)).NOx_calculation(),
            Noise(self.get_metrics(problem), self.architecture).noise_calculation()
        )

        print("----------------------------------------------------------------------------", file=fp, flush=True)
        print("                             DISCIPLINE OUTPUT", file=fp, flush=True)
        print("   System weight   Max length   Max diameter   Take-off NOx   Take-off noise  ", file=fp, flush=True)
        print("        [kg]           [m]          [m]        [g/kg fuel]        [dB]  ", file=fp, flush=True)
        print(" %12.2f  %11.2f  %11.2f  %14.2f  %14.2f" % data, file=fp, flush=True)
        print("----------------------------------------------------------------------------", file=fp, flush=True)

    def get_metrics(self, problem: om.Problem) -> OperatingMetrics:
        def _float(val):
            return float(np.atleast_1d(val)[0])

        # Check if ITB, AB and mixed nozzle are present
        itb_present = False
        ab_present = False
        burners = self.architecture.get_elements_by_type(Burner)
        for burner in range(len(burners)):
            if burners[burner].name == 'itb':
                itb_present = True
            elif burners[burner].name == 'ab':
                ab_present = True
        mixed_nozzle = False
        nozzles = self.architecture.get_elements_by_type(Nozzle)
        for nozzle in range(len(nozzles)):
            if nozzles[nozzle].name == 'nozzle_joint':
                mixed_nozzle = True

        return OperatingMetrics(
            fuel_flow=_float(problem.get_val(self.name+'.perf.Wfuel', units=units.MASS_FLOW, get_remote=None)),
            area_inlet=_float(problem.get_val('%s.%s.Fl_O:stat:area' % (self.name, self.inlet_el_name), units=units.AREA, get_remote=None)),
            mass_flow=_float(problem.get_val('%s.%s.Fl_O:stat:W' % (self.name, self.inlet_el_name),
                                             units=units.MASS_FLOW, get_remote=None)),
            thrust=_float(problem.get_val(self.name+'.perf.Fn', units=units.FORCE, get_remote=None)),
            tsfc=_float(problem.get_val(self.name+'.perf.TSFC', units=units.TSFC, get_remote=None)),
            opr=_float(problem.get_val(self.name+'.perf.OPR', get_remote=None)),
            area_jet=_float(problem.get_val('%s.%s.Fl_O:stat:area' % (self.name, 'nozzle_core' if not mixed_nozzle else 'nozzle_joint'), units=units.AREA, get_remote=None)),
            v_jet=_float(problem.get_val('%s.%s.Fl_O:stat:V' % (self.name, 'nozzle_core' if not mixed_nozzle else 'nozzle_joint'), units=units.VELOCITY, get_remote=None)),
            mach_jet=_float(problem.get_val('%s.%s.Fl_O:stat:MN' % (self.name, 'nozzle_core' if not mixed_nozzle else 'nozzle_joint'), get_remote=None)),
            p_atm=_float(problem.get_val('%s.%s.Fl_O:tot:P' % (self.name, 'fc'), units=units.PRESSURE, get_remote=None)),
            t_atm=_float(problem.get_val('%s.%s.Fl_O:tot:T' % (self.name, 'fc'), units=units.TEMPERATURE, get_remote=None)),
            p_burner_in=_float(problem.get_val('%s.%s.Fl_I:tot:P' % (self.name, 'burner'), units=units.PRESSURE, get_remote=None)),
            t_burner_in=_float(problem.get_val('%s.%s.Fl_I:tot:T' % (self.name, 'burner'), units=units.TEMPERATURE, get_remote=None)),
            p_itb_in=_float(problem.get_val('%s.%s.Fl_I:tot:P' % (self.name, 'itb'), units=units.PRESSURE, get_remote=None)) if itb_present else 0,
            t_itb_in=_float(problem.get_val('%s.%s.Fl_I:tot:T' % (self.name, 'itb'), units=units.TEMPERATURE, get_remote=None)) if itb_present else 0,
            p_ab_in=_float(problem.get_val('%s.%s.Fl_I:tot:P' % (self.name, 'ab'), units=units.PRESSURE, get_remote=None)) if ab_present else 0,
            t_ab_in=_float(problem.get_val('%s.%s.Fl_I:tot:T' % (self.name, 'ab'), units=units.TEMPERATURE, get_remote=None)) if ab_present else 0,
            p_jet=_float(problem.get_val('%s.%s.Fl_O:tot:P' % (self.name, 'nozzle_core' if not mixed_nozzle else 'nozzle_joint'), units=units.PRESSURE, get_remote=None)),
            t_jet=_float(problem.get_val('%s.%s.Fl_O:tot:T' % (self.name, 'nozzle_core' if not mixed_nozzle else 'nozzle_joint'), units=units.TEMPERATURE, get_remote=None)),
        )


class ArchitectureMultiPointCycle(pyc.MPCycle):
    """A cycle evaluating the architecture at multiple operating conditions."""

    def __init__(self, architecture: TurbofanArchitecture, design_condition: DesignCondition,
                 evaluate_conditions: List[EvaluateCondition] = None, max_iter=20):
        super(ArchitectureMultiPointCycle, self).__init__()

        self.architecture: TurbofanArchitecture = architecture
        self.design_condition: DesignCondition = design_condition
        self.evaluate_conditions: List[EvaluateCondition] = evaluate_conditions or []
        self._max_iter = max_iter

        self.balance_connected_des_od = set()

    @property
    def conditions(self) -> List[OperatingCondition]:
        return [self.design_condition]+list(self.evaluate_conditions)

    @property
    def _cycles(self) -> List[ArchitectureCycle]:
        des_cycles = [self._des_pnt] if self._des_pnt is not None else []
        return des_cycles+self._od_pnts

    def setup(self):
        self._add_design_point()
        self._add_off_design_points()

    def _add_design_point(self):
        condition = self.design_condition
        self.pyc_add_pnt(condition.name, self._get_cycle(condition))

        for element in self.architecture.elements:
            element.add_cycle_params(self)

    def _add_off_design_points(self):
        if len(self.evaluate_conditions) == 0:
            return

        for condition in self.evaluate_conditions:
            self.pyc_add_pnt(condition.name, self._get_cycle(condition))

        for element in self.architecture.elements:
            element.connect_des_od(self)

        for condition in self.conditions:
            condition.balancer.connect_des_od(self, self.architecture)

    def _get_cycle(self, condition: OperatingCondition) -> ArchitectureCycle:
        return ArchitectureCycle(self.architecture, condition, max_iter=self._max_iter)

    def print_results(self, problem: om.Problem, fp=sys.stdout):
        for cycle in self._cycles:
            cycle.print_results(problem, fp=fp)

    def get_metrics(self, problem: om.Problem) -> Dict[OperatingCondition, OperatingMetrics]:
        return {cycle.condition: cycle.get_metrics(problem) for cycle in self._cycles}


class CycleBuilder:
    """Builds a pyCycle OpenMDAO Problem that analyzes/sizes the turbofan architecture for the given analysis
    problem."""

    def __init__(self, architecture: TurbofanArchitecture, problem: AnalysisProblem, max_iter=20):
        self.architecture = architecture
        self.problem = problem
        self._max_iter = max_iter
        self._mp_cycle: Optional[ArchitectureMultiPointCycle] = None

    @property
    def conditions(self) -> List[OperatingCondition]:
        return [self.problem.design_condition]+list(self.problem.evaluate_conditions)

    def get_problem(self) -> om.Problem:

        # Construct problem
        problem = om.Problem()
        problem.model = self._mp_cycle = self._get_multi_point_cycle()
        problem.setup(check=False)

        # Define the design point
        for condition in self.conditions:
            condition.set_values(problem)

        des_con_name = self.problem.design_condition.name
        eval_con_names = [condition.name for condition in self.problem.evaluate_conditions]
        for element in self.architecture.elements:
            element.set_problem_values(problem, des_con_name, eval_con_names)

        return problem

    def _get_multi_point_cycle(self) -> ArchitectureMultiPointCycle:
        return ArchitectureMultiPointCycle(
            self.architecture, self.problem.design_condition, evaluate_conditions=self.problem.evaluate_conditions,
            max_iter=self._max_iter)

    @staticmethod
    def view_n2(problem: om.Problem, **kwargs):
        om.n2(problem, **kwargs)

    @staticmethod
    def run(problem: om.Problem, print_solver=True):
        problem.set_solver_print(level=-1)
        if print_solver:
            problem.set_solver_print(level=2, depth=1)

        with warnings.catch_warnings():
            # warnings.simplefilter('ignore', Sol)
            np.seterr(all='ignore')
            problem.run_model()

            # pyCycle may set numpy error raising behavior: reset to ignore here
            np.seterr(all='ignore')

    def print_results(self, problem: om.Problem, fp=sys.stdout):
        self._mp_cycle.print_results(problem, fp=fp)

    def get_metrics(self, problem: om.Problem) -> Dict[OperatingCondition, OperatingMetrics]:
        return self._mp_cycle.get_metrics(problem)


class Balancer:
    """A balancer defines how certain values should be implicitly equated to each other so that calculations are
    consistent (i.e. they solve the residuals)."""

    balance_name = 'engine_balance'

    def apply(self, cycle: ArchitectureCycle, architecture: TurbofanArchitecture):
        """Add balances and set initial guesses."""
        raise NotImplementedError

    def connect_des_od(self, mp_cycle: ArchitectureMultiPointCycle, architecture: TurbofanArchitecture):
        """Connect design parameters to off-design (evaluation) parameters"""
        raise NotImplementedError
