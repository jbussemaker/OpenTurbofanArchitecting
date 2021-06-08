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

from enum import Enum
import openmdao.api as om
from typing import *
import pycycle.api as pyc
from dataclasses import dataclass, field
import open_turb_arch.evaluation.architecture.units as units
from open_turb_arch.evaluation.architecture.architecture import ArchElement

__all__ = ['Inlet', 'Duct', 'Splitter', 'Mixer', 'BleedInter', 'BleedIntra', 'Nozzle', 'NozzleType', 'HeatExchanger']


@dataclass(frozen=False)
class Inlet(ArchElement):
    target: ArchElement = None  # Output flow connection target
    mach: float = .6  # Reference Mach number for loss calculations
    p_recovery: float = 1.  # Fraction of the recovered total pressure (ram recovery)

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        el = pyc.Inlet(design=design, thermo_data=thermo_data, elements=pyc.AIR_ELEMENTS)
        cycle.pyc_add_element(self.name, el)

        if design:
            el.set_input_defaults('MN', self.mach)
        return el

    def connect(self, cycle: pyc.Cycle):
        cycle.pyc_connect_flow('fc.Fl_O', self.name+'.Fl_I', connect_w=False)
        self._connect_flow_target(cycle, self.target)

    def add_cycle_params(self, mp_cycle: pyc.MPCycle):
        mp_cycle.pyc_add_cycle_param(self.name+'.ram_recovery', self.p_recovery)

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        mp_cycle.pyc_connect_des_od(self.name+'.Fl_O:stat:area', self.name+'.area')


@dataclass(frozen=False)
class Duct(ArchElement):
    target: ArchElement = None
    mach: float = .3  # Reference Mach number for loss calculations
    p_loss_frac: float = 0.  # Pressure loss as fraction of incoming pressure (dPqP)
    fuel_in_air: bool = False
    statics: bool = True
    design: bool = True

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        elements = pyc.AIR_FUEL_ELEMENTS if self.fuel_in_air else pyc.AIR_ELEMENTS
        el = pyc.Duct(thermo_data=thermo_data, elements=elements, statics=self.statics, design=design)
        cycle.pyc_add_element(self.name, el)

    def connect(self, cycle: pyc.Cycle):
        self._connect_flow_target(cycle, self.target)

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        mp_cycle.pyc_connect_des_od(self.name+'.Fl_O:stat:area', self.name+'.area')


@dataclass(frozen=False)
class Splitter(ArchElement):
    target_core: ArchElement = None  # Core flow connection target
    target_bypass: ArchElement = None  # Bypass flow connection target
    bpr: float = 1.  # Bypass ratio: ratio of bypassing flow (output 2) to core flow (output 1)
    core_mach: float = .3  # Reference Mach number for loss calculations
    bypass_mach: float = .3  # Reference Mach number for loss calculations
    flow_out: str = None

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        el = pyc.Splitter(design=design, thermo_data=thermo_data, elements=pyc.AIR_ELEMENTS)
        cycle.pyc_add_element(self.name, el)

        if design:
            el.set_input_defaults('BPR', self.bpr)
            el.set_input_defaults('MN1', self.core_mach)
            el.set_input_defaults('MN2', self.bypass_mach)
        return el

    def connect(self, cycle: pyc.Cycle):
        self._connect_flow_target(cycle, self.target_core, out_flow='Fl_O1')
        self._connect_flow_target(cycle, self.target_bypass, in_flow='Fl_I' if self.flow_out is None else self.flow_out, out_flow='Fl_O2')

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        mp_cycle.pyc_connect_des_od(self.name+'.Fl_O1:stat:area', self.name+'.area1')
        mp_cycle.pyc_connect_des_od(self.name+'.Fl_O2:stat:area', self.name+'.area2')


@dataclass(frozen=False)
class Mixer(ArchElement):
    source_1: ArchElement = None
    source_2: ArchElement = None
    target: ArchElement = None
    mach: float = .3  # Reference Mach number for loss calculations

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        el = pyc.Mixer(design=design, thermo_data=thermo_data, Fl_I1_elements=pyc.AIR_FUEL_ELEMENTS, Fl_I2_elements=pyc.AIR_ELEMENTS)
        cycle.pyc_add_element(self.name, el)
        return el

    def connect(self, cycle: pyc.Cycle):
        self._connect_flow_target(cycle, self.target)

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        mp_cycle.pyc_connect_des_od(self.name+'.Fl_O:stat:area', self.name+'.area')
        mp_cycle.pyc_connect_des_od(self.name+'.Fl_I1_calc:stat:area', self.name+'.Fl_I1_stat_calc.area')

    def __repr__(self):
        if self.source_1 is None:
            s1_str = 'None'
        else:
            s1_str = '%s(name=%r, ...)' % (self.source_1.__class__.__name__, self.source_1.name)

        if self.source_2 is None:
            s2_str = 'None'
        else:
            s2_str = '%s(name=%r, ...)' % (self.source_2.__class__.__name__, self.source_2.name)

        return 'Mixer(source_1=%s, source_2=%s, target=%r, mach=%r)' % (s1_str, s2_str, self.target, self.mach)


@dataclass(frozen=False)
class BleedInter(ArchElement):
    target: ArchElement = None
    target_bleed: List[str] = field(default_factory=lambda: [])
    mach: float = .3  # Reference Mach number for loss calculations
    source_frac_w: List[float] = field(default_factory=lambda: [])
    target_frac_p: float = 1.0
    fuel_in_air: bool = False
    bleed_names: List[str] = field(default_factory=lambda: [])

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        elements = pyc.AIR_FUEL_ELEMENTS if self.fuel_in_air else pyc.AIR_ELEMENTS
        el = pyc.BleedOut(thermo_data=thermo_data, elements=elements, design=design, bleed_names=self.bleed_names)
        cycle.pyc_add_element(self.name, el)

    def connect(self, cycle: pyc.Cycle):
        self._connect_flow_target(cycle, self.target)
        for i, bleed_name in enumerate(self.bleed_names):
            if 'atmos' not in bleed_name:
                cycle.pyc_connect_flow('%s.%s' % (self.name, bleed_name), '%s.%s' % (self.target_bleed[i], bleed_name), connect_stat=False)

    def add_cycle_params(self, mp_cycle: pyc.MPCycle):
        for i, bleed_name in enumerate(self.bleed_names):
            mp_cycle.pyc_add_cycle_param('%s.%s' % (self.name, bleed_name) + ':frac_W', self.source_frac_w[i])
            if 'atmos' not in bleed_name:
                mp_cycle.pyc_add_cycle_param('%s.%s' % (self.target_bleed[i], bleed_name) + ':frac_P', self.target_frac_p)

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        mp_cycle.pyc_connect_des_od(self.name+'.Fl_O:stat:area', self.name+'.area')


@dataclass(frozen=False)
class BleedIntra(ArchElement):
    source: ArchElement = None
    target: List[str] = field(default_factory=lambda: [])
    mach: float = .3  # Reference Mach number for loss calculations
    source_frac_w: List[float] = field(default_factory=lambda: [])
    source_frac_p: float = 1.0
    source_frac_work: float = 1.0
    target_frac_p: float = 1.0
    fuel_in_air: bool = False
    bleed_names: List[str] = field(default_factory=lambda: [])

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        pass

    def connect(self, cycle: pyc.Cycle):
        for i, bleed_name in enumerate(self.bleed_names):
            if 'atmos' not in bleed_name:
                cycle.pyc_connect_flow('%s.%s' % (self.source.name, bleed_name), '%s.%s' % (self.target[i], bleed_name), connect_stat=False)

    def add_cycle_params(self, mp_cycle: pyc.MPCycle):
        for i, bleed_name in enumerate(self.bleed_names):
            mp_cycle.pyc_add_cycle_param('%s.%s' % (self.source.name, bleed_name) + ':frac_W', self.source_frac_w[i])          # bleed mass flow fraction (W_bld/W_in)
            mp_cycle.pyc_add_cycle_param('%s.%s' % (self.source.name, bleed_name) + ':frac_P', self.source_frac_p)          # bleed pressure fraction ((P_bld-P_in)/(P_out-P_in))
            mp_cycle.pyc_add_cycle_param('%s.%s' % (self.source.name, bleed_name) + ':frac_work', self.source_frac_work)       # bleed work fraction ((h_bld-h_in)/(h_out-h_in))
            if 'atmos' not in bleed_name:
                mp_cycle.pyc_add_cycle_param('%s.%s' % (self.target[i], bleed_name) + ':frac_P', self.target_frac_p)

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        pass


class NozzleType(Enum):
    CV = 'CV'
    CD = 'CD'
    CV_CD = 'CD_CV'


@dataclass(frozen=False)
class Nozzle(ArchElement):
    target: ArchElement = None  # This can be left to None to "connect" to the environment
    type: NozzleType = NozzleType.CV
    v_loss_coefficient: float = 1.  # Ratio of outgoing to incoming flow velocity
    fuel_in_air: bool = True  # Whether the air mix contains fuel at the nozzle
    flow_out: str = None

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        elements = pyc.AIR_FUEL_ELEMENTS if self.fuel_in_air else pyc.AIR_ELEMENTS
        el = pyc.Nozzle(nozzType=self.type.value, lossCoef='Cv', thermo_data=thermo_data, elements=elements)
        cycle.pyc_add_element(self.name, el)
        return el

    def connect(self, cycle: pyc.Cycle):
        if self.target is None:
            cycle.connect('fc.Fl_O:stat:P', self.name+'.Ps_exhaust')
        else:
            self._connect_flow_target(cycle, self.target, in_flow=self.flow_out)

    def add_cycle_params(self, mp_cycle: pyc.MPCycle):
        mp_cycle.pyc_add_cycle_param(self.name+'.Cv', self.v_loss_coefficient)

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        pass


@dataclass(frozen=False)
class HeatExchanger(ArchElement):
    target_fluid: ArchElement = None
    target_coolant: ArchElement = None
    fluid: ArchElement = None
    coolant: ArchElement = None
    length: float = 0.1  # Length of heat exchanger tube
    radius: float = 0.1  # Radius of heat exchanger tube
    number: int = 4  # Number of heat exchanger tubes
    h_overall: float = 1/100  # Overall heat transfer coefficient
    ff_core: float = 0.0005  # Core friction factor
    ff_bypass: float = 0.005  # Bypass friction factor
    flow_out_fluid: str = None
    flow_out_coolant: str = None

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        el = pyc.HeatExchanger(thermo_data=thermo_data, Fl_I1_elements=pyc.AIR_ELEMENTS, Fl_I2_elements=pyc.AIR_ELEMENTS)
        cycle.pyc_add_element(self.name, el)
        return el

    def connect(self, cycle: pyc.Cycle):
        self._connect_flow_target(cycle, self.target_fluid, out_flow='Fl_O1', in_flow='Fl_I' if self.flow_out_fluid is None else self.flow_out_fluid)
        self._connect_flow_target(cycle, self.target_coolant, out_flow='Fl_O2', in_flow='Fl_I' if self.flow_out_coolant is None else self.flow_out_coolant)

    def add_cycle_params(self, mp_cycle: pyc.MPCycle):
        mp_cycle.pyc_add_cycle_param(self.name+'.length_hex', self.length, units=units.LENGTH)
        mp_cycle.pyc_add_cycle_param(self.name+'.radius_hex', self.radius, units=units.LENGTH)
        mp_cycle.pyc_add_cycle_param(self.name+'.number_hex', self.number)
        mp_cycle.pyc_add_cycle_param(self.name+'.h_overall', self.h_overall, units=units.HTC)
        mp_cycle.pyc_add_cycle_param(self.name+'.ff_core', self.ff_core)
        mp_cycle.pyc_add_cycle_param(self.name+'.ff_bypass', self.ff_bypass)

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        pass
