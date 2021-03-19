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

__all__ = ['Weight', 'Length', 'Diameter', 'NOx', 'Noise']


@dataclass(frozen=False)
class Weight:
    """Calculates the weight of the aircraft engine. Equations are taken from Design Methodologies
     for Aerodynamics, Structures, Weight, and Thermodynamic Cycles (MIT, 2010)."""

    ops_metrics: OperatingMetrics
    architecture: TurbofanArchitecture

    @staticmethod
    def check_architecture(ops_metrics: OperatingMetrics, architecture: TurbofanArchitecture):

        # Check whether gearbox is present
        gear = architecture.get_elements_by_type(Gearbox) is not None

        # Check if fan and CRTF are present
        fan_present = False
        crtf_present = False
        compressors = architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan':
                fan_present = True
            if compressors[compressor].name == 'crtf':
                crtf_present = True

        # Get massflow rate and OPR
        massflow = ops_metrics.mass_flow
        opr = ops_metrics.opr

        # Get BPR
        bpr = architecture.get_elements_by_type(Splitter)[0].bpr if fan_present else 0

        return fan_present, crtf_present, gear, massflow, opr, bpr

    def weight_calculation(self, ops_metrics: OperatingMetrics, architecture: TurbofanArchitecture):

        fan_present, crtf_present, gear, massflow, opr, bpr = self.check_architecture(ops_metrics, architecture)

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
        if len(architecture.get_elements_by_type(Burner)) != 1:  # ITB
            weight *= 1.05**(len(architecture.get_elements_by_type(Burner))-1)

        if not fan_present:  # Turbojet
            weight *= 0.75
            if len(architecture.get_elements_by_type(Compressor)) != 1:  # Multiple shafts
                weight *= 1.1**(len(architecture.get_elements_by_type(Compressor))-1)
        else:  # Turbofan
            if len(architecture.get_elements_by_type(Compressor)) != 2:  # Multiple shafts
                weight *= 1.1**(len(architecture.get_elements_by_type(Compressor))-2)

        # Based on EU project COBRA: https://cordis.europa.eu/project/id/605379/reporting
        if crtf_present:
            weight *= 1.1

        if len(architecture.get_elements_by_type(Mixer)) == 1:  # Mixed nacelle
            weight *= 1.1

        return weight


@dataclass(frozen=False)
class Length:
    """Calculates the length of the aircraft engine. Equations are taken from Design Methodologies
     for Aerodynamics, Structures, Weight, and Thermodynamic Cycles (MIT, 2010)."""

    ops_metrics: OperatingMetrics
    architecture: TurbofanArchitecture

    @staticmethod
    def check_architecture(ops_metrics: OperatingMetrics, architecture: TurbofanArchitecture):

        # Check whether gearbox is present
        gear = architecture.get_elements_by_type(Gearbox) is not None

        # Check if fan is present
        fan_present = False
        crtf_present = False
        compressors = architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan':
                fan_present = True
            if compressors[compressor].name == 'crtf':
                crtf_present = True

        # Get massflow rate and OPR
        massflow = ops_metrics.mass_flow
        opr = ops_metrics.opr

        # Get BPR
        bpr = architecture.get_elements_by_type(Splitter)[0].bpr if fan_present else 0

        return fan_present, crtf_present, gear, massflow, opr, bpr

    def length_calculation(self, ops_metrics: OperatingMetrics, architecture: TurbofanArchitecture):

        fan_present, crtf_present, gear, massflow, opr, bpr = self.check_architecture(ops_metrics, architecture)

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
        if len(architecture.get_elements_by_type(Burner)) != 1:  # ITB
            length *= 1.05**(len(architecture.get_elements_by_type(Burner))-1)

        if not fan_present:  # Turbojet
            length *= 0.75
            if len(architecture.get_elements_by_type(Compressor)) != 1:  # Multiple shafts
                length *= 1.1**(len(architecture.get_elements_by_type(Compressor))-1)
        else:  # Turbofan
            if len(architecture.get_elements_by_type(Compressor)) != 2:  # Multiple shafts
                length *= 1.1**(len(architecture.get_elements_by_type(Compressor))-2)

        # Based on EU project COBRA: https://cordis.europa.eu/project/id/605379/reporting
        if crtf_present:
            length *= 1.1

        return length


@dataclass(frozen=False)
class Diameter:
    """Calculates the maximum diameter of the aircraft engine. Equations are taken from Aerospace
    Design and Systems Engineering Elements I (TU Delft, 2017)."""

    ops_metrics: OperatingMetrics
    architecture: TurbofanArchitecture

    @staticmethod
    def check_architecture(ops_metrics: OperatingMetrics, architecture: TurbofanArchitecture):

        # Check if fan is present
        fan_present = False
        compressors = architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan':
                fan_present = True

        # Check if separate or mixed nacelle
        config = 'mixed' if len(architecture.get_elements_by_type(Mixer)) == 1 else 'separate'

        # Get massflow rate and BPR
        massflow = ops_metrics.mass_flow
        bpr = architecture.get_elements_by_type(Splitter)[0].bpr if fan_present else 0

        # Get necessary elements from operating metrics
        p_atm = ops_metrics.p_atm  # atmospheric pressure [Pa]
        t_atm = ops_metrics.t_atm+273.15  # atmospheric temperature [K]

        return config, massflow, bpr, p_atm, t_atm

    def diameter_calculation(self, ops_metrics: OperatingMetrics, architecture: TurbofanArchitecture):

        config, massflow, bpr, p_atm, t_atm = self.check_architecture(ops_metrics, architecture)
        c_atm = sqrt(1.4*287.05*t_atm)
        rho_atm = p_atm/(287.05*t_atm)

        # Calculate maximum diameter with TU Delft equation
        dsdi = 0.05*(1 + 0.1*rho_atm*c_atm/massflow + 3*bpr/(1+bpr))
        di = 1.65*sqrt((massflow/rho_atm/c_atm+0.005)/(1-dsdi**2))
        cl, dl = (9.8, 0.05) if config == 'mixed' else (7.8, 0.1)
        ln = cl*(sqrt(massflow/rho_atm/c_atm*(1+0.2*bpr)/(1+bpr))+dl)
        diameter = di + 0.06*0.65*ln + 0.03

        return diameter  # m


@dataclass(frozen=False)
class NOx:
    """Calculates the NOx emissions of the aircraft engine. Equations are taken from GasTurb 13
    Design and Off-Design Performance of Gas Turbines (GasTurb GmbH, 2018)."""

    ops_metrics: OperatingMetrics
    architecture: TurbofanArchitecture

    @staticmethod
    def check_architecture(ops_metrics: OperatingMetrics):

        # Get pressure and temperature from operating metrics
        pressure = ops_metrics.p_burner_in/10**3  # burner inlet pressure [kPa]
        temperature = ops_metrics.t_burner_in+273.15  # burner inlet temperature [K]

        return pressure, temperature

    def NOx_calculation(self, ops_metrics: OperatingMetrics):

        pressure, temperature = self.check_architecture(ops_metrics)

        # Calculate NOx with GasTurb equation
        NOx = 32*(pressure/2964.5)**0.4*exp((temperature-826.26)/194.39+(6.29-100*0.03)/53.2)

        return NOx/10**3  # (gram NOx)/kN


@dataclass(frozen=False)
class Noise:
    """Calculates the Noise emissions of the aircraft engine. Equations are taken from Interim
    Prediction Method for Jet Noise (Stone, 1974)"""

    ops_metrics: OperatingMetrics
    architecture: TurbofanArchitecture

    @staticmethod
    def check_architecture(ops_metrics: OperatingMetrics, architecture: TurbofanArchitecture):

        # Check if CRTF is present
        crtf_present = False
        compressors = architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'crtf':
                crtf_present = True

        # Get necessary elements from operating metrics
        area_jet = ops_metrics.area_jet  # outlet area of the jet nozzle [m2]
        v_jet = ops_metrics.v_jet  # outlet velocity of the jet nozzle [m/s]
        p_atm = ops_metrics.p_atm  # atmospheric pressure [Pa]
        t_atm = ops_metrics.t_atm+273.15  # atmospheric temperature [K]
        p_jet = ops_metrics.p_jet  # jet nozzle exit pressure [Pa]
        t_jet = ops_metrics.t_jet+273.15  # jet nozzle exit temperature [K]

        return crtf_present, area_jet, v_jet, p_atm, t_atm, p_jet, t_jet

    def noise_calculation(self, ops_metrics: OperatingMetrics, architecture: TurbofanArchitecture):

        crtf_present, area_jet, v_jet, p_atm, t_atm, p_jet, t_jet = self.check_architecture(ops_metrics, architecture)
        c_atm = sqrt(1.4*287.05*t_atm)
        rho_atm = p_atm/(287.05*t_atm)
        rho_jet = p_jet/(287.05*p_jet)

        # Calculate noise with Stone equation
        OASPL_nozzle = 141 + 10*log10(area_jet) + 10*log10((v_jet/c_atm)**7.5/(1+0.01*(v_jet/c_atm)**4.5)) \
                       + 10*(3*(v_jet/c_atm)**3.5/(0.6+(v_jet/c_atm)**3.5)-1)*log10(rho_jet/rho_atm)

        # Based on EU project COBRA: https://cordis.europa.eu/project/id/605379/reporting
        if crtf_present:
            OASPL_nozzle -= 5

        return OASPL_nozzle  # dB
