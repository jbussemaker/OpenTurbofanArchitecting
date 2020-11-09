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
import pycycle.api as pyc
from dataclasses import dataclass
from open_turb_arch.evaluation.architecture.architecture import ArchElement

__all__ = ['Inlet', 'Duct', 'Splitter', 'Bleed', 'Nozzle', 'NozzleType']


@dataclass(frozen=False)
class Inlet(ArchElement):
    target: ArchElement = None  # Output flow connection target
    mach: float = .6  # Reference Mach number for loss calculations
    p_recovery: float = 1.  # Fraction of the recovered total pressure (ram recovery)

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        el = pyc.Inlet(design=design, thermo_data=thermo_data, elements=pyc.AIR_MIX)
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

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        raise NotImplementedError

    def connect(self, cycle: pyc.Cycle):
        raise NotImplementedError

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        raise NotImplementedError


@dataclass(frozen=False)
class Splitter(ArchElement):
    target_core: ArchElement = None  # Core flow connection target
    target_bypass: ArchElement = None  # Bypass flow connection target
    bpr: float = 1.  # Bypass ratio: ratio of bypassing flow (output 2) to core flow (output 1)
    core_mach: float = .3  # Reference Mach number for loss calculations
    bypass_mach: float = .3  # Reference Mach number for loss calculations

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        raise NotImplementedError

    def connect(self, cycle: pyc.Cycle):
        raise NotImplementedError

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        raise NotImplementedError


@dataclass(frozen=False)
class Bleed(ArchElement):
    target: ArchElement = None
    mach: float = .3  # Reference Mach number for loss calculations
    mass_flow: float = 0.  # Bleed air mass flow [kg/s]

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        raise NotImplementedError

    def connect(self, cycle: pyc.Cycle):
        raise NotImplementedError

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        raise NotImplementedError


class NozzleType(Enum):
    CV = 'CV'
    CD = 'CD'
    CV_CD = 'CD_CV'


@dataclass(frozen=False)
class Nozzle(ArchElement):
    target: ArchElement = None  # This can be left to None to "connect" to the environment
    type: NozzleType = NozzleType.CV
    v_loss_coefficient: float = 1.  # Ratio of outgoing to incoming flow velocity

    def add_element(self, cycle: pyc.Cycle, thermo_data, design: bool) -> om.Group:
        el = pyc.Nozzle(nozzType=self.type.value, lossCoef='Cv', thermo_data=thermo_data, elements=pyc.AIR_FUEL_MIX)
        cycle.pyc_add_element(self.name, el)
        return el

    def connect(self, cycle: pyc.Cycle):
        if self.target is None:
            cycle.connect('fc.Fl_O:stat:P', self.name+'.Ps_exhaust')
        else:
            self._connect_flow_target(cycle, self.target)

    def add_cycle_params(self, mp_cycle: pyc.MPCycle):
        mp_cycle.pyc_add_cycle_param(self.name+'.Cv', self.v_loss_coefficient)

    def connect_des_od(self, mp_cycle: pyc.MPCycle):
        pass
