from open_turb_arch.evaluation.architecture import *

__all__ = ['get_turbojet_architecture']


def get_turbojet_architecture() -> TurbofanArchitecture:
    inlet = Inlet(
        name='inlet',
        mach=.6, p_recovery=1,
    )

    inlet.target = compressor = Compressor(
        name='compressor', map=CompressorMap.AXI_5,
        mach=.02, pr=13.5, eff=.83,
    )

    compressor.target = burner = Burner(
        name='burner', fuel=FuelType.JET_A,
        mach=.02, p_loss_frac=.03,
    )

    burner.target = turbine = Turbine(
        name='turbine', map=TurbineMap.LPT_2269,
        mach=.4, eff=.86,
    )

    turbine.target = nozzle = Nozzle(
        name='nozzle', type=NozzleType.CD,
        v_loss_coefficient=.99,
    )

    shaft = Shaft(
        name='shaft', connections=[compressor, turbine],
        rpm_design=8070, power_loss=0.,
    )

    bleed = Bleed(
        name='bleed', case='intra', bleed_names=['bld'], connections=['lpc', 'lpt']
    )

    return TurbofanArchitecture(elements=[inlet, compressor, burner, turbine, nozzle, shaft, bleed])
