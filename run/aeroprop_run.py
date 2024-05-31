# Standard Python modules
import argparse
import json
import os
from pprint import pprint as pp
from pathlib import Path

# External modules
from aeroprop_mda import Top
from mpi4py import MPI
import openmdao.api as om

# Local modules
from geometry.geo_vars import geo_vars
from utils.add_geo_dvs import add_geo_dvs
from utils.point_specs import get_point_specs

# ==============================================================================
# Command Line Arguments
# ==============================================================================
parser = argparse.ArgumentParser()
parser.add_argument(
    "--task",
    default="opt",
    nargs="*",
    help="Task to be done. See the bottom half of aero_run file for the available options",
)
parser.add_argument("--totals_type", default="opt_prob", help="Type of totals check to be run.")

# CFD parameters
parser.add_argument("--input_dir", default="./INPUT", help="Input file directory")
parser.add_argument("--output_dir", default="./OUTPUT/", help="Output file directory")
parser.add_argument(
    "--level",
    default="L2",
    choices=["L0", "L0.5", "L1", "L1.5", "L2"],
    help="Level for the CFD mesh. A larger level is coarser, finest is L0",
)
parser.add_argument(
    "--debug",
    default=False,
    action="store_true",
    help="Prints some debugging info for CFD surfaces",
)
parser.add_argument("--version", default="v1", help="Version of the mesh and geometry.")
parser.add_argument(
    "--mb",
    default=False,
    action="store_true",
    help="Flag to use the multiblock meshes. Only for debugging",
)

# fan design parameters. we will always use cruise0 as the design case
parser.add_argument(
    "--model",
    default="az",
    choices=["az", "bc"],
    help="Fan model to use in CFD. Has to be either actuator zone (az) or boundary conditions (bc)",
)
parser.add_argument("--fpr", type=float, default=1.30, help="Design FPR at nominal cruise")
parser.add_argument(
    "--thrust",
    type=float,
    default=6000,
    help="Design thrust at nominal cruise. This is the half-body value so the total thrust is twice this number",
)
parser.add_argument(
    "--feedfwd",
    default=False,
    action="store_true",
    help="Flag to use the feed-forward coupling. only works with the AZ version",
)

# Optimization parameters
parser.add_argument(
    "--driver", default="snopt", choices=["scipy", "snopt"], help="Optimizer to use. Only tested with SNOPT"
)

parser.add_argument("--msl", type=float, default=0.1, help="Major step limit parameter for SNOPT")
parser.add_argument("--timelimit", type=float, default=7200.0, help="Time limit set in SNOPT.")



args = parser.parse_args()

# check the output directory here and create if necessary
Path(args.output_dir).mkdir(parents=True, exist_ok=True)
# ==============================================================================
# Print argument values
# ==============================================================================
if MPI.COMM_WORLD.rank == 0:
    # Echo the args:
    print("Arguments are:", flush=True)
    for arg in vars(args):
        print(arg, ":", getattr(args, arg), flush=True)


# ==============================================================================
# OpenMDAO Setup
# ==============================================================================
# --- Create the problem and add the model ---
prob = om.Problem()
prob.model = model = Top(
    model=args.model,
    output_dir=args.output_dir,
    input_dir=args.input_dir,
    level=args.level,
    multiblock=args.mb,
    debug=args.debug,
    feedfwd=args.feedfwd,
    target_net_thrust=args.thrust,
)

mini_opt_analysis = False

# --- Get the point specs ---
pt_specs = get_point_specs(feedfwd=args.feedfwd)


if "opt" in args.task or "bc" in args.task or "check_totals" in args.task:

    # --- Add the objective function ---
    if args.model == "az":
        model.add_objective("cruise0.coupling.prop.total_shaft_power", cache_linear_solution=True, ref=1000.0)
    else:
        model.add_objective("cruise0.coupling.prop.prop:shaft_power", cache_linear_solution=True, ref=1000.0)

    # --- Constraints ---
    # Design point constraints

    # Fan pressure ratio constraint on design point
    model.add_constraint("cruise0.coupling.prop.FPR", equals=args.fpr, cache_linear_solution=True, ref=1.0)

    if args.model=='az':
        # Net thrust constraint on design point for AZ
        model.add_constraint("cruise0.coupling.prop.Fn", equals=args.thrust, cache_linear_solution=True, ref=1000.0)

    # Fan face mach number constraint on design point
    model.add_constraint("cruise0.coupling.aero.mavgmn_fan_face", upper=0.6, cache_linear_solution=True, ref=1.0)

    # BC constraints
    if args.model == "bc":

        #we need to satisfy the 3 conservation equations with constraints
        model.add_constraint("cruise0.coupling.balance.res_V", equals=0.0, cache_linear_solution=True, ref=100.0)
        model.add_constraint(
            "cruise0.coupling.balance.res_mdot", equals=0.0, cache_linear_solution=True, ref=100.0
        )
        model.add_constraint(
            "cruise0.coupling.balance.res_area", equals=0.0, cache_linear_solution=True, ref=10.0
        )

        # net thrust constraint
        model.add_constraint(
            "cruise0.coupling.balance.res_net_thrust", equals=0.0, cache_linear_solution=True, ref=1000.0
        )


    # Add thickness constraints
    model.add_constraint("geo.upper_thickness", lower=1.0, upper=3.0, cache_linear_solution=True, ref=1.0)
    model.add_constraint("geo.right_thickness", lower=1.0, upper=3.0, cache_linear_solution=True, ref=1.0)

    # --- Design Variables ---
    # Thrust is added for AZ version
    if args.model=='az':
            model.add_design_var("aero_dvs.thrust_cruise0", lower=5000.0, upper=16000, ref=10000)

    # Add DVs for the BC only
    if args.model == "bc" :

        model.add_design_var("aero_dvs.fan_exit_mach_cruise0", lower=0.2, upper=0.6, ref=1.0)
        model.add_design_var("aero_dvs.Ps_cruise0", lower=20000, upper=40000, ref=10000)
        model.add_design_var("aero_dvs.Ptot_cruise0", lower=30000, upper=60000, ref=10000)
        model.add_design_var("aero_dvs.Ttot_cruise0", lower=200.0, upper=400.0, ref=100.0)


    # Geometric DVs
    # Add the number of the cross section and angle that you want to
    # add to these lists
    nacelle_xsecs = [0, 1, 3, 4, 5, 6, 7]
    nacelle_angles = [0, 3, 5, 6, 7]
    core_xsecs = [3]
    core_angles = [3]

    # Create a filter that has the component, group, and number for
    # the cross sections and angles we want to add as DVs
    geo_dv_filter = {
        "Nacelle": [f"XSecCurve_{i}" for i in nacelle_xsecs] + [f"XSec_{i}" for i in nacelle_angles],
        "Core": [f"XSecCurve_{i}" for i in core_xsecs] + [f"XSec_{i}" for i in core_angles],
    }

    # add geometric dvs
    add_geo_dvs(model, geo_vars, geo_dv_filter)

# --- Optimizer settings ---
if args.driver == "snopt":
    prob.driver = om.pyOptSparseDriver(
        optimizer="SNOPT", debug_print=["desvars", "ln_cons", "nl_cons", "objs", "totals"]
    )

    # determine feasibility tolerance based on run type
    if args.model == "bc":
        maj_feas_tol = 1e-10
    else:
        maj_feas_tol = 1e-6

    prob.driver.opt_settings = {
        "Major feasibility tolerance": maj_feas_tol,
        "Major optimality tolerance": 1e-6,
        "Verify level": 0,
        "Major iterations limit": 600,
        "Minor iterations limit": 1000000,
        "Iterations limit": 1500000,
        "Major step limit": args.msl,
        "Hessian full memory": None,
        "Hessian frequency": 40,
        "Hessian updates": 40,
        "Print file": f"{args.output_dir}/SNOPT_print.out",
        "Summary file": f"{args.output_dir}/summary_SNOPT.out",
        "Problem Type": "Minimize",
        "Penalty parameter": 1.0,
        "Time Limit": args.timelimit,  # time limit in seconds
    }

    prob.driver.hist_file = os.path.join(args.output_dir, "opt.hst")

    # Add recorders to the driver and problem
    recorder = om.SqliteRecorder(os.path.join(args.output_dir, "recorder.sql"))
    prob.driver.add_recorder(recorder)

elif args.driver == "scipy":
    prob.driver = om.ScipyOptimizeDriver(
        optimizer="SLSQP", debug_print=["desvars", "ln_cons", "nl_cons", "objs"], disp=True
    )

# --- Setup the model ---
prob.setup(mode="rev")
om.n2(prob, show_browser=False, outfile=os.path.join(args.output_dir, f"pod_{args.model}.html"))

# analysis task
if "run" in args.task:
    # write volume solutions with this mode
    model.aero_builder.solver.setOption("writevolumesolution", True)
    model.aero_builder.solver.setOption("writetecplotsurfacesolution", True)
    prob.run_model()
    model.list_outputs(units=True)

# optimization task
if "opt" in args.task:
    prob.run_driver()
    prob.model.list_outputs(units=True)
    # do one last call to write the volume files
    prob.model.aero_builder.solver.setOption("writevolumesolution", True)
    prob.model.aero_builder.solver.setOption("writetecplotsurfacesolution", True)

    scenario = getattr(prob.model, "cruise0")
    scenario.aero_post.nom_write_solution(baseName="opt_final_cruise0")

# checking total derivatives
if "check_totals" in args.task:
    prob.run_model()
    prob.check_totals()
