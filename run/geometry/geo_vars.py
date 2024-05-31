# Standard Python modules
from collections import namedtuple

# --- OpenVSP component names ---
comp_nacelle = "Nacelle"
comp_core = "Core"

# --- Named tuple for geometry variables ---
GeoVar = namedtuple("GeoVar", ["comp", "group", "var", "lower", "upper", "ref", "dh"])


# list of variables to add:
geo_vars = [
    # CORE PARAMETERS
    # plug diameter (aligned with nacelle TE) @ 30 in
    # only allow this to reduce by half, effectively creating a thickness constraint.
    # one or two cases will run up to the bound
    GeoVar(comp=comp_core, group="XSecCurve_3", var="Circle_Diameter", lower=15.0, upper=60.0, ref=1.0, dh=1e-6),
    # tangent at the plug location @ -5 degrees
    GeoVar(comp=comp_core, group="XSec_3", var="TopLAngle", lower=-60, upper=60, ref=1.0, dh=1e-6),
    # NACELLE PARAMETERS
    # nacelle inner TE @ 65 in
    GeoVar(comp=comp_nacelle, group="XSecCurve_0", var="Circle_Diameter", lower=30, upper=150, ref=1.0, dh=1e-6),
    # nacelle outer TE @ 65.2 in
    GeoVar(comp=comp_nacelle, group="XSecCurve_8", var="Circle_Diameter", lower=30, upper=150, ref=1.0, dh=1e-6),
    # fan exit @ 75 in
    GeoVar(comp=comp_nacelle, group="XSecCurve_1", var="Circle_Diameter", lower=30, upper=150, ref=1.0, dh=1e-6),
    # fan face @ 75 in
    GeoVar(comp=comp_nacelle, group="XSecCurve_2", var="Circle_Diameter", lower=30, upper=150, ref=1.0, dh=1e-6),
    # inlet inner @ H 74 in W 74 in
    GeoVar(comp=comp_nacelle, group="XSecCurve_3", var="Ellipse_Height", lower=30, upper=150, ref=1.0, dh=1e-6),
    GeoVar(comp=comp_nacelle, group="XSecCurve_3", var="Ellipse_Width", lower=30, upper=150, ref=1.0, dh=1e-6),
    # inlet LE @ H 80 in W 80 in
    GeoVar(comp=comp_nacelle, group="XSecCurve_4", var="Ellipse_Height", lower=30, upper=150, ref=1.0, dh=1e-6),
    GeoVar(comp=comp_nacelle, group="XSecCurve_4", var="Ellipse_Width", lower=30, upper=150, ref=1.0, dh=1e-6),
    # inlet outer @ H 87 in W 87 in
    GeoVar(comp=comp_nacelle, group="XSecCurve_5", var="Ellipse_Height", lower=30, upper=150, ref=1.0, dh=1e-6),
    GeoVar(comp=comp_nacelle, group="XSecCurve_5", var="Ellipse_Width", lower=30, upper=150, ref=1.0, dh=1e-6),
    # mid-outer @ 87.5 in
    GeoVar(comp=comp_nacelle, group="XSecCurve_6", var="Circle_Diameter", lower=30, upper=150, ref=1.0, dh=1e-6),
    # aft-outer @ 82 in
    GeoVar(comp=comp_nacelle, group="XSecCurve_7", var="Circle_Diameter", lower=30, upper=150, ref=1.0, dh=1e-6),
    # nacelle angles
    # inner TE left @ 175
    GeoVar(comp=comp_nacelle, group="XSec_0", var="TopLAngle", lower=120, upper=240, ref=1.0, dh=1e-6),
    # for the following 3 elliptical sections
    # inner inlet L=R @ 180
    GeoVar(comp=comp_nacelle, group="XSec_3", var="TopLAngle", lower=120, upper=240, ref=1.0, dh=1e-6),
    # inlet LE L=R @ 90
    # disable this, we want to keep the LE at 90 degrees
    # GeoVar(comp=comp_nacelle, group='XSec_4', var='TopLAngle', lower=60, upper=120, ref=1.0, dh=1e-6),
    # outer inlet L=R @ 2
    GeoVar(comp=comp_nacelle, group="XSec_5", var="TopLAngle", lower=-60, upper=60, ref=1.0, dh=1e-6),
    # outer mid L=R @ -1
    GeoVar(comp=comp_nacelle, group="XSec_6", var="TopLAngle", lower=-60, upper=60, ref=1.0, dh=1e-6),
    # outer nozzle L=R @ -8
    GeoVar(comp=comp_nacelle, group="XSec_7", var="TopLAngle", lower=-60, upper=60, ref=1.0, dh=1e-6),
]
