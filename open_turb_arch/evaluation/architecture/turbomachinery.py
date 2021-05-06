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
from enum import Enum
import openmdao.api as om
import pycycle.api as pyc
from dataclasses import dataclass, field
import open_turb_arch.evaluation.architecture.units as units
from open_turb_arch.evaluation.architecture.architecture import ArchElement

__all__ = ['Compressor', 'CompressorMap', 'Burner', 'FuelType', 'Turbine', 'TurbineMap', 'Gearbox', 'Shaft']


@dataclass(frozen=False)
class BaseTurboMachinery(ArchElement):

    def __post_init__(self):
        self.__shaft = None

    @property
    def shaft(self):
        return self.__shaft

    @shaft.setter
    def shaft(self, shaft: 'Shaft'):
        self.__shaft = shaft

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        raise NotImplementedError

    def connect(self, cycle: pyc.Cycle):
        raise NotImplementedError

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        raise NotImplementedError


class CompressorMap(Enum):
    AXI_5 = 'AXI5'
    LPC = 'LPCMap'
    HPC = 'HPCMap'
    Fan = 'FanMap'


@dataclass(frozen=False)
class Compressor(BaseTurboMachinery):
    target: ArchElement = None
    map: CompressorMap = CompressorMap.AXI_5
    mach: float = .01  # Reference Mach number for loss calculations
    pr: float = 5.  # Compression pressure ratio
    eff: float = 1.  # Enthalpy rise efficiency (<1 is less efficient)
    bleed_names: List[str] = field(default_factory=lambda: [])
    offtake_bleed: bool = None  # Compressor for extraction bleed offtake
    flow_out: str = None

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        if self.shaft is None:
            raise ValueError('Not connected to shaft: %r' % self)

        map_data = getattr(pyc, self.map.value)
        el = pyc.Compressor(map_data=map_data, design=design, thermo_data=thermo_data, elements=pyc.AIR_ELEMENTS, bleed_names=self.bleed_names)
        cycle.pyc_add_element(self.name, el, promotes_inputs=[('Nmech', self.shaft.name+'_Nmech')])

        if design:
            el.set_input_defaults('MN', self.mach)
        return el

    def connect(self, cycle: pyc.Cycle):
        self._connect_flow_target(cycle, self.target, in_flow='Fl_I' if self.flow_out is None else self.flow_out)

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        for param in ['s_PR', 's_Wc', 's_eff', 's_Nc']:
            mp_cycle.pyc_connect_des_od('%s.%s' % (self.name, param), '%s.%s' % (self.name, param))

        mp_cycle.pyc_connect_des_od(self.name+'.Fl_O:stat:area', self.name+'.area')

    def set_problem_values(self, problem: om.Problem, des_con_name: str, eval_con_names: List[str]):
        problem.set_val('%s.%s.PR' % (des_con_name, self.name), self.pr)
        problem.set_val('%s.%s.eff' % (des_con_name, self.name), self.eff)


class FuelType(Enum):
    JET_A = 'Jet-A(g)'  # Standard jet fuel
    JP_7 = 'JP-7'  # Supersonic
    H2 = 'H2'  # Innovative
    CH4 = 'Methane'
    H2O = 'Water'


@dataclass(frozen=False)
class Burner(ArchElement):
    target: ArchElement = None
    fuel: FuelType = FuelType.JET_A  # Type of fuel
    mach: float = .01  # Reference Mach number for loss calculations
    p_loss_frac: float = 0.  # Pressure loss as fraction of incoming pressure (dPqP)
    fuel_in_air: bool = False  # Whether the air mix contains fuel at the burner entry
    main: bool = True  # Whether the Burner is the main burner of the engine
    far: float = 0  # Fuel-air ratio in case of non-main burner

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        inflow_elements = pyc.AIR_FUEL_ELEMENTS if self.fuel_in_air else pyc.AIR_ELEMENTS
        el = pyc.Combustor(design=design, thermo_data=thermo_data, inflow_elements=inflow_elements,
                           air_fuel_elements=pyc.AIR_FUEL_ELEMENTS, fuel_type=self.fuel.value)
        cycle.pyc_add_element(self.name, el)

        if design:
            el.set_input_defaults('MN', self.mach)
            if not self.main:
                el.set_input_defaults('Fl_I:FAR', self.far)
        return el

    def connect(self, cycle: pyc.Cycle):
        self._connect_flow_target(cycle, self.target)

    def add_cycle_params(self, mp_cycle: pyc.MPCycle):
        mp_cycle.pyc_add_cycle_param(self.name+'.dPqP', self.p_loss_frac)

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        mp_cycle.pyc_connect_des_od(self.name+'.Fl_O:stat:area', self.name+'.area')


class TurbineMap(Enum):
    LPT_2269 = 'LPT2269'
    LPT = 'LPTMap'
    HPT = 'HPTMap'


@dataclass(frozen=False)
class Turbine(BaseTurboMachinery):
    target: ArchElement = None
    map: TurbineMap = TurbineMap.LPT_2269
    mach: float = .4  # Reference Mach number for loss calculations
    eff: float = 1.  # Enthalpy rise efficiency (<1 is less efficient)
    bleed_names: List[str] = field(default_factory=lambda: [])

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        if self.shaft is None:
            raise ValueError('Not connected to shaft: %r' % self)

        map_data = getattr(pyc, self.map.value)
        el = pyc.Turbine(map_data=map_data, design=design, thermo_data=thermo_data, elements=pyc.AIR_FUEL_ELEMENTS, bleed_names=self.bleed_names)
        cycle.pyc_add_element(self.name, el, promotes_inputs=[('Nmech', self.shaft.name+'_Nmech')])

        if design:
            el.set_input_defaults('MN', self.mach)
        return el

    def connect(self, cycle: pyc.Cycle):
        self._connect_flow_target(cycle, self.target)

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        for param in ['s_PR', 's_Wp', 's_eff', 's_Np']:
            mp_cycle.pyc_connect_des_od('%s.%s' % (self.name, param), '%s.%s' % (self.name, param))

        mp_cycle.pyc_connect_des_od(self.name+'.Fl_O:stat:area', self.name+'.area')

    def set_problem_values(self, problem: om.Problem, des_con_name: str, eval_con_names: List[str]):
        problem.set_val('%s.%s.eff' % (des_con_name, self.name), self.eff)


@dataclass(frozen=False)
class Gearbox(BaseTurboMachinery):
    fan_shaft: ArchElement = None
    core_shaft: ArchElement = None

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:

        el = pyc.Gearbox()
        cycle.pyc_add_element(self.name, el, promotes_inputs=[('N_in', self.core_shaft.name+'_Nmech'), ('N_out', self.fan_shaft.name+'_Nmech')])
        return el

    def connect(self, cycle: pyc.Cycle):
        cycle.connect(self.name+'.trq_in', '%s.trq_%d' % (self.core_shaft.name, 2))   # LP shaft
        cycle.connect(self.name+'.trq_out', '%s.trq_%d' % (self.fan_shaft.name, 1))    # Fan

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        pass


@dataclass(frozen=False)
class Shaft(ArchElement):
    connections: List[BaseTurboMachinery] = None
    rpm_design: float = 10000.  # Design shaft rotation speed [rpm]
    power_loss: float = 0.  # Fraction of power lost
    offtake_shaft: bool = False  # Shaft for power offtake
    power_offtake: float = 0.  # Amount of power offtake

    def __post_init__(self):
        self._set_shaft_ref()

    def _set_shaft_ref(self):
        for conn in self.connections:
            if not isinstance(conn, Gearbox):
                if conn.shaft is not None and conn.shaft is not self:
                    raise ValueError('Shaft already set: %r' % conn)
                conn.shaft = self

    def add_element_prepare(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        self._set_shaft_ref()

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        if self.connections is None or len(self.connections) < 2:
            raise ValueError('Shaft should at least connect two turbomachinery elements!')

        el = pyc.Shaft(num_ports=len(self.connections))
        cycle.pyc_add_element(self.name, el, promotes_inputs=[('Nmech', self.name+'_Nmech')])

        if design:
            cycle.set_input_defaults(self.name +'_Nmech', self.rpm_design, units=units.RPM)
        return el

    def connect(self, cycle: pyc.Cycle):
        for i, element in enumerate(self.connections):
            if not isinstance(element, Gearbox):
                cycle.connect(element.name+'.trq', '%s.trq_%d' % (self.name, i))

    def add_cycle_params(self, mp_cycle: pyc.MPCycle):
        mp_cycle.pyc_add_cycle_param(self.name+'.fracLoss', self.power_loss)
        if self.offtake_shaft:
            mp_cycle.pyc_add_cycle_param(self.name+'.HPX', self.power_offtake, units='W')

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        pass
