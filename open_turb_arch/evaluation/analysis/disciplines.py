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
import numpy as np
from dataclasses import dataclass
from open_turb_arch.evaluation.architecture import *
from open_turb_arch.evaluation.analysis import *

__all__ = ['Weight', 'Length', 'Diameter', 'NOx', 'Noise']


@dataclass(frozen=False)
class Weight:
    """Calculates the weight of the integrated aircraft engine. Equations are taken from Design Methodologies
     for Aerodynamics, Structures, Weight, and Thermodynamic Cycles (Greitzer & Slater, 2010) and Analysis of
     Turbofan Propulsion System Weight and Dimensions (Waters & Schairer, 1977) and Advanced Aircraft Design:
     Conceptual Design, Analysis and Optimization of Subsonic Civil Airplanes (Torenbeek, 2013)."""

    ops_metrics: OperatingMetrics
    architecture: TurbofanArchitecture

    def check_architecture(self):

        # Check whether gearbox and heat exchanger are present
        gear = False if not self.architecture.get_elements_by_type(Gearbox) else True
        hex = False if not self.architecture.get_elements_by_type(HeatExchanger) else True
        hex_length = self.architecture.get_elements_by_type(HeatExchanger)[0].length if hex else 0
        hex_radius = self.architecture.get_elements_by_type(HeatExchanger)[0].radius if hex else 0
        hex_number = self.architecture.get_elements_by_type(HeatExchanger)[0].number if hex else 0
        hex_area = 2*np.pi*hex_radius*hex_length*hex_number

        # Check if fan and CRTF are present
        fan_present = False
        crtf_present = False
        compressors = self.architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan':
                fan_present = True
            if compressors[compressor].name == 'crtf':
                crtf_present = True

        # Get massflow rate, OPR and BPR
        massflow = self.ops_metrics.mass_flow
        opr = self.ops_metrics.opr
        bpr = self.architecture.get_elements_by_type(Splitter)[0].bpr if fan_present else 0

        return fan_present, crtf_present, gear, hex_area, massflow, opr, bpr

    def weight_calculation(self):

        fan_present, crtf_present, gear, hex_area, massflow, opr, bpr = self.check_architecture()

        # Calculate engine weight with MIT WATE++ equations
        if not gear:  # No gearbox present
            a = (1.538*10)*bpr**2 + (4.011*10**2)*bpr + 631.5
            b = (1.057*10**(-3))*bpr**2 - (3.693*10**(-2))*bpr + 1.171
            c = (-1.022*10**(-2))*bpr + 0.232
        else:  # Gearbox present
            a = (-6.204*10**(-1))*bpr**2 + (2.373*10**2)*bpr + 1702
            b = (5.845*10**(-5))*bpr**2 - (5.866*10**(-3))*bpr + 1.045
            c = (-1.918*10**(-3))*bpr + 0.0677
        massflow_core = massflow/(1+bpr)
        weight_engine = (a*(massflow_core*2.2046226218/100)**b*(opr/40)**c)/2.2046226218

        # Add engine weight changes based on MIT component weights, unless mentioned otherwise
        if not fan_present:  # Turbojet
            weight_engine *= 3
        if len(self.architecture.get_elements_by_type(Turbine)) != 2:  # No 2-shaft engine
            weight_engine *= 1.1**(len(self.architecture.get_elements_by_type(Turbine))-2)
        if len(self.architecture.get_elements_by_type(Burner)) != 1:  # ITB
            weight_engine *= 1.05**(len(self.architecture.get_elements_by_type(Burner))-1)
        if crtf_present:  # CRTF
            weight_engine *= 1.1  # Based on EU project COBRA: https://cordis.europa.eu/project/id/605379/reporting
        if hex_area != 0:  # intercooler
            weight_engine += hex_area*0.001*4510*10  # titanium density = 4510 kg/m3, intercooler pipe thickness = 1 mm, pipes = 10% of installation

        # Get nacelle lengths and diameters
        l_fancowl = Length(self.ops_metrics, self.architecture).length_calculation()[1]
        l_gg = Length(self.ops_metrics, self.architecture).length_calculation()[3]
        d_inlet = Diameter(self.ops_metrics, self.architecture).diameter_calculation()[0]
        d_fan_outlet = Diameter(self.ops_metrics, self.architecture).diameter_calculation()[2]
        d_gg_inlet = Diameter(self.ops_metrics, self.architecture).diameter_calculation()[3]
        d_gg_outlet = Diameter(self.ops_metrics, self.architecture).diameter_calculation()[4]

        # Calculate nacelle weight based on Proesmans estimation
        area_fancowl = l_fancowl*pi*(d_inlet+d_fan_outlet)/2
        area_gg = l_gg*pi*(d_gg_inlet+d_gg_outlet)/2
        fancowl_perc_nozzle = min(0.5*((d_inlet+d_fan_outlet)/2)/l_fancowl, 0.33)
        gg_perc_nozzle = min(0.5*((d_gg_inlet+d_gg_outlet)/2)/l_gg, 0.33) if l_gg != 0 else 0
        weight_fancowl = area_fancowl*(1-fancowl_perc_nozzle)*17.1+area_fancowl*fancowl_perc_nozzle*73.2  # Fan cowl weight estimation
        weight_gg = area_gg*(1-gg_perc_nozzle)*17.1+area_gg*gg_perc_nozzle*73.2  # Gas generator weight estimation
        weight_nacelle = weight_fancowl+weight_gg

        # Calculate pylon and total system weight based on Torenbeek estimation
        weight_total = (weight_engine+weight_nacelle)/0.86
        weight_pylon = 0.14*weight_total

        return weight_total, weight_engine, weight_nacelle, weight_pylon  # kg


@dataclass(frozen=False)
class Length:
    """Calculates the length of the aircraft engine. Equations are taken from De Berekening van het
    Omspoeld Gondeloppervlak van Enkel- en Dubbelstroom Straalmotoren voor Civiele VLiegtuigen
    (Torenbeek & Berenschot, 1983)."""

    ops_metrics: OperatingMetrics
    architecture: TurbofanArchitecture

    def check_architecture(self):

        # Check whether gearbox is present
        gear = False if not self.architecture.get_elements_by_type(Gearbox) else True

        # Check if fan and CRTF are present
        fan_present = False
        crtf_present = False
        compressors = self.architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan':
                fan_present = True
            if compressors[compressor].name == 'crtf':
                crtf_present = True

        # Check if separate or mixed nacelle
        config = 'mixed' if len(self.architecture.get_elements_by_type(Mixer)) == 1 else 'separate'

        # Get necessary elements from operating metrics
        massflow = self.ops_metrics.mass_flow
        bpr = self.architecture.get_elements_by_type(Splitter)[0].bpr if fan_present else 0

        return fan_present, crtf_present, config, gear, massflow, bpr

    def length_calculation(self):

        fan_present, crtf_present, config, gear, massflow, bpr = self.check_architecture()

        # Define necessary parameters
        t_atm = 288.15  # According to ISA atmosphere
        rho_atm = 1.225  # According to ISA atmosphere
        c_atm = sqrt(1.4*287.05*t_atm)
        cl, dl, phi = (12, 0, 1) if not fan_present else ((9.8, 0.05, 1) if config == 'mixed' else (7.8, 0.1, 0.625))
        beta = 0.21+0.12/sqrt(phi-0.3) if (fan_present and config == 'separate') else 0.35

        # Calculate nacelle length with Torenbeek & Berenschot equations
        l_nacelle = cl*(sqrt(massflow/rho_atm/c_atm*(1+0.2*bpr)/(1+bpr))+dl)*0.67

        # Add length changes based on estimated component lengths, unless mentioned otherwise
        if not fan_present:  # Turbojet
            l_nacelle *= 1.5
        if len(self.architecture.get_elements_by_type(Turbine)) != 2:  # No 2-shaft engine
            l_nacelle *= 1.1**(len(self.architecture.get_elements_by_type(Turbine))-2)
        if len(self.architecture.get_elements_by_type(Burner)) != 1:  # ITB
            l_nacelle *= 1.1**(len(self.architecture.get_elements_by_type(Burner))-1)
        if crtf_present:  # CRTF
            l_nacelle *= 1.1  # Based on EU project COBRA: https://cordis.europa.eu/project/id/605379/reporting

        # Calculate engine component lengths with Torenbeek & Berenschot equations
        l_fancowl = phi*l_nacelle  # Fan cowl length
        l_dmax = beta*l_fancowl  # Location at which engine diameter is max
        l_gg = (1-phi)*l_nacelle  # Exposed gas generator length
        l_cone = 0.5*l_gg  # Cone length --> estimation

        return l_nacelle, l_fancowl, l_dmax, l_gg, l_cone  # m


@dataclass(frozen=False)
class Diameter:
    """Calculates the diameter of the aircraft engine. Equations are taken from De Berekening van het
    Omspoeld Gondeloppervlak van Enkel- en Dubbelstroom Straalmotoren voor Civiele VLiegtuigen
    (Torenbeek & Berenschot, 1983)."""

    ops_metrics: OperatingMetrics
    architecture: TurbofanArchitecture

    def check_architecture(self):

        # Check if fan is present
        fan_present = False
        compressors = self.architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'fan':
                fan_present = True

        # Check if separate or mixed nacelle
        config = 'separate' if not self.architecture.get_elements_by_type(Mixer) else 'mixed'

        # Get massflow rate and BPR
        massflow = self.ops_metrics.mass_flow
        area_inlet = self.ops_metrics.area_inlet
        bpr = self.architecture.get_elements_by_type(Splitter)[0].bpr if fan_present else 0

        return fan_present, config, massflow, area_inlet, bpr

    def diameter_calculation(self):

        fan_present, config, massflow, area_inlet, bpr = self.check_architecture()
        l_nacelle = Length(self.ops_metrics, self.architecture).length_calculation()[0]
        phi = 1 if not fan_present else (1 if config == 'mixed' else 0.625)

        # Define necessary parameters
        t_atm = 288.15  # According to ISA atmosphere
        rho_atm = 1.225  # According to ISA atmosphere
        c_atm = sqrt(1.4*287.05*t_atm)

        # Calculate maximum diameter with TU Delft equation
        d_inlet = sqrt(4/pi*area_inlet)  # Nacelle inlet diameter
        d_max = (d_inlet + 0.06*phi*l_nacelle + 0.03)*1.25  # Maximum nacelle diameter
        d_fan_outlet = d_max*(1-(1/3)*phi**2)  # Fan exit diameter
        d_gg_inlet = d_fan_outlet*((0.089*massflow/rho_atm/c_atm*bpr+4.5)/(0.067*massflow/rho_atm/c_atm*bpr+5.8))**2  # Gas generator inlet diameter
        d_gg_outlet = 0.55*d_gg_inlet  # Gas generator outlet diameter
        d_cone_inlet = 0.55*d_gg_outlet  # Cone inlet diameter --> estimation

        return d_inlet, d_max, d_fan_outlet, d_gg_inlet, d_gg_outlet, d_cone_inlet  # m


@dataclass(frozen=False)
class NOx:
    """Calculates the NOx emissions of the aircraft engine. Equations are taken from GasTurb 13:
    Design and Off-Design Performance of Gas Turbines (Kurzke, 2018)."""

    ops_metrics: OperatingMetrics

    def check_architecture(self):

        # Get pressure and temperature from operating metrics
        p_burner = self.ops_metrics.p_burner_in/10**3  # main burner inlet pressure [kPa]
        t_burner = self.ops_metrics.t_burner_in+273.15  # main burner inlet temperature [K]
        p_itb = self.ops_metrics.p_itb_in/10**3  # ITB inlet pressure [kPa]
        t_itb = self.ops_metrics.t_itb_in+273.15  # ITB inlet temperature [K]
        p_ab = self.ops_metrics.p_ab_in/10**3  # AB inlet pressure [kPa]
        t_ab = self.ops_metrics.t_ab_in+273.15  # AB inlet temperature [K]

        return p_burner, t_burner, p_itb, t_itb, p_ab, t_ab

    def NOx_calculation(self):

        p_burner, t_burner, p_itb, t_itb, p_ab, t_ab = self.check_architecture()

        # Calculate NOx with GasTurb equation
        NOx_burner = 32*(p_burner/2964.5)**0.4*exp((t_burner-826.26)/194.39+(6.29-100*0.03)/53.2)
        NOx_itb = 32*(p_itb/2964.5)**0.4*exp((t_itb-826.26)/194.39+(6.29-100*0.03)/53.2)
        NOx_ab = 32*(p_ab/2964.5)**0.4*exp((t_ab-826.26)/194.39+(6.29-100*0.03)/53.2)
        NOx_burner = NOx_burner if (NOx_itb+NOx_ab == 0) else 0
        NOx_total = NOx_burner+NOx_itb+NOx_ab

        return NOx_total  # (gram NOx)/(kg fuel)


@dataclass(frozen=False)
class Noise:
    """Calculates the Noise emissions of the aircraft engine. Equations are taken from Interim
    Prediction Method for Jet Noise (Stone, 1974)."""

    ops_metrics: OperatingMetrics
    architecture: TurbofanArchitecture

    def check_architecture(self):

        # Check if CRTF is present
        crtf_present = False
        compressors = self.architecture.get_elements_by_type(Compressor)
        for compressor in range(len(compressors)):
            if compressors[compressor].name == 'crtf':
                crtf_present = True

        # Get necessary elements from operating metrics
        area_jet = self.ops_metrics.area_jet  # outlet area of the jet nozzle [m2]
        v_jet = self.ops_metrics.v_jet  # outlet velocity of the jet nozzle [m/s]
        p_atm = self.ops_metrics.p_atm  # atmospheric pressure [Pa]
        t_atm = self.ops_metrics.t_atm+273.15  # atmospheric temperature [K]
        p_jet = self.ops_metrics.p_jet  # jet nozzle exit pressure [Pa]
        t_jet = self.ops_metrics.t_jet+273.15  # jet nozzle exit temperature [K]

        return crtf_present, area_jet, v_jet, p_atm, t_atm, p_jet, t_jet

    def noise_calculation(self):

        crtf_present, area_jet, v_jet, p_atm, t_atm, p_jet, t_jet = self.check_architecture()
        c_atm = sqrt(1.4*287.05*t_atm)
        rho_atm = p_atm/(287.05*t_atm)
        rho_jet = p_jet/(287.05*p_jet)
        rho_isa = 1.225
        c_isa = sqrt(1.4*287.05*288.15)

        # Calculate noise with Stone equation
        OASPL_nozzle = 141 + 10*log10(area_jet*(rho_atm/rho_isa)**2*(c_atm/c_isa)**2) + \
                       10*log10((v_jet/c_atm)**7.5/(1+0.01*(v_jet/c_atm)**4.5)) \
                       + 10*(3*(v_jet/c_atm)**3.5/(0.6+(v_jet/c_atm)**3.5)-1)*log10(rho_jet/rho_atm)

        # Add noise changes based on components
        if crtf_present:  # Based on EU project COBRA: https://cordis.europa.eu/project/id/605379/reporting
            OASPL_nozzle -= 5

        return OASPL_nozzle  # dB
