# Standard Python modules
from collections import namedtuple

InitialConditions = namedtuple(
    "InitialConditions", ["alpha", "mach", "altitude", "thrust0", "heat0", "Ps0", "Ptot0", "Ttot0"]
)

def get_point_specs(feedfwd: bool = False):
    # flight conditions
    alpha = {
        "cruise0": 0.0,
    }

    mach = {
        "cruise0": 0.785,
    }

    altitude = {
        "cruise0": 36000 * 0.3048,
    }

    # initial thrust and heat
    thrust0 = {
        "cruise0": 10000.0,
    }

    if not feedfwd:
        heat0 = {
            "cruise0": 44145.9869,
        }
    else:
        heat0 = {
            "cruise0": 0.0,
        }

    # initial values for BC variables
    # these are set based on AZ runs
    Ps0 = {
        "cruise0": 28510.34452618,
    }

    Ptot0 = {
        "cruise0": 42580.44533603,
    }

    Ttot0 = {
        "cruise0": 260.13922384,
    }

    return InitialConditions(
        alpha=alpha,
        mach=mach,
        altitude=altitude,
        thrust0=thrust0,
        heat0=heat0,
        Ps0=Ps0,
        Ptot0=Ptot0,
        Ttot0=Ttot0,
    )


DV_UNITS = {
    "alpha": "deg",
    "mach": None,
    "altitude": "m",
    "thrust": "N",
    "heat": "W",
    "Ps": "Pa",
    "Ptot": "Pa",
    "Ttot": "degK",
}

# These are specs for all points
NOMINAL_SPECS = {
    "alpha": 0.0,
    "mach": 0.785,
    "altitude": 36000 * 0.3048,
    "pstar": 3600.0,  # kW full-body
    "thrust0": 6000.0,  # N half-body
    "heat0": 44145.9869,  # W half-body
    "Ps0": 28510.34452618,  # Pa
    "Ptot0": 42580.44533603,  # Pa
    "Ttot0": 260.13922384,  # K
}

# These come from the STARC-ABL wing
AREA_REF = 105.8 / 2
CHORD_REF = 3.264
