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


from math import *
from dataclasses import dataclass
from open_turb_arch.evaluation.architecture import *
from open_turb_arch.evaluation.analysis import *

__all__ = ['Weight', 'Length', 'NOx']


@dataclass(frozen=False)
class Weight:
    """Calculates the weight of the aircraft engine."""

    ops_metrics: OperatingMetrics
    architecture: TurbofanArchitecture

    @staticmethod
    def check_architecture(ops_metrics: OperatingMetrics, architecture: TurbofanArchitecture):

        # Check whether gearbox is present
        gear = architecture.get_elements_by_type(Gearbox) is not None

        # Check if fan is present
        fan_present = False
        compressors = architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan':
                fan_present = True

        # Get massflow rate and OPR
        massflow = ops_metrics.mass_flow
        opr = ops_metrics.opr

        # Get BPR
        bpr = architecture.get_elements_by_type(Splitter)[0].bpr if fan_present else 0

        return fan_present, gear, massflow, opr, bpr

    def weight_calculation(self, ops_metrics, architecture: TurbofanArchitecture):

        fan_present, gear, massflow, opr, bpr = self.check_architecture(ops_metrics, architecture)

        # Calculate weight with MIT WATE++ equations
        if not gear:
            a = (1.809*10)*bpr**2 + (4.769*10**2)*bpr + 701.3
            b = (1.077*10**(-3))*bpr**2 - (3.716*10**(-2))*bpr + 1.190
            c = (-1.058*10**(-2))*bpr + 0.326
        else:
            a = (-6.590*10**(-1))*bpr**2 + (2.928*10**2)*bpr + 1915
            b = (6.784*10**(-5))*bpr**2 - (6.488*10**(-3))*bpr + 1.061
            c = (-1.969*10**(-3))*bpr + 0.0711
        weight = (a*(massflow*2.2046226218/100)**b*(opr/40)**c)/2.2046226218

        # Add weight changes based on components
        if len(architecture.get_elements_by_type(Burner)) != 1:     # ITB
            weight *= 1.05**(len(architecture.get_elements_by_type(Burner))-1)

        if not fan_present:     # Turbojet
            weight *= 0.75
            if len(architecture.get_elements_by_type(Compressor)) != 1:  # Multiple shafts
                weight *= 1.1**(len(architecture.get_elements_by_type(Compressor))-1)
        else:       # Turbofan
            if len(architecture.get_elements_by_type(Compressor)) != 2:  # Multiple shafts
                weight *= 1.1**(len(architecture.get_elements_by_type(Compressor))-2)

        if len(architecture.get_elements_by_type(Mixer)) == 1:      # Mixed nacelle
            weight *= 1.1

        return weight


@dataclass(frozen=False)
class Length:
    """Calculates the length of the aircraft engine."""

    ops_metrics: OperatingMetrics
    architecture: TurbofanArchitecture

    @staticmethod
    def check_architecture(ops_metrics: OperatingMetrics, architecture: TurbofanArchitecture):

        # Check whether gearbox is present
        gear = architecture.get_elements_by_type(Gearbox) is not None

        # Check if fan is present
        fan_present = False
        compressors = architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan':
                fan_present = True

        # Get massflow rate and OPR
        massflow = ops_metrics.mass_flow
        opr = ops_metrics.opr

        # Get BPR
        bpr = architecture.get_elements_by_type(Splitter)[0].bpr if fan_present else 0

        return fan_present, gear, massflow, opr, bpr

    def length_calculation(self, ops_metrics, architecture: TurbofanArchitecture):

        fan_present, gear, massflow, opr, bpr = self.check_architecture(ops_metrics, architecture)

        # Calculate length with MIT WATE++ equations
        if not gear:
            a = (6.156*10**2)*bpr**2 + (1.357*10**1)*bpr + 27.51
            b = (6.892*10**(-4))*bpr**2 - (2.714*10**(-2))*bpr + 0.505
            c = 0.129
        else:
            a = (-1.956*10**(-2))*bpr**2 + (1.244*10**0)*bpr + 77.1
            b = (7.354*10**(-6))*bpr**2 - (3.335*10**(-3))*bpr + 0.388
            c = -0.032
        length = (a*(massflow*2.2046226218/100)**b*(opr/40)**c)*0.0254

        # Add length changes based on components
        if len(architecture.get_elements_by_type(Burner)) != 1:     # ITB
            length *= 1.05**(len(architecture.get_elements_by_type(Burner))-1)

        if not fan_present:     # Turbojet
            length *= 0.75
            if len(architecture.get_elements_by_type(Compressor)) != 1:  # Multiple shafts
                length *= 1.1**(len(architecture.get_elements_by_type(Compressor))-1)
        elif fan_present:       # Turbofan
            if len(architecture.get_elements_by_type(Compressor)) != 2:  # Multiple shafts
                length *= 1.1**(len(architecture.get_elements_by_type(Compressor))-2)

        return length


@dataclass(frozen=False)
class NOx:
    """Calculates the NOx emissions of the aircraft engine."""

    ops_metrics: OperatingMetrics
    architecture: TurbofanArchitecture

    @staticmethod
    def check_architecture(ops_metrics: OperatingMetrics):

        pressure = ops_metrics.p3/10**3  # burner inlet pressure [kPa]
        temperature = ops_metrics.t3+273.15  # burner inlet temperature [K]

        return pressure, temperature

    def NOx_calculation(self, ops_metrics):

        pressure, temperature = self.check_architecture(ops_metrics)
        NOx = 32*(pressure/2964.5)**0.4*exp((temperature-826.26)/194.39+(6.29-100*0.03)/53.2)  # equation from GasTurb

        return NOx/10**3  # (gram NOx)/kN
