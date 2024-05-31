# Standard Python modules
import os

# External modules
from adflow.mphys import ADflowBuilder
from baseclasses import AeroProblem
from mphys.multipoint import Multipoint
from mphys.scenario_aeropropulsive import ScenarioAeropropulsive
from mpi4py import MPI
import numpy as np
import openmdao.api as om
from pygeo.mphys import OM_DVGEOCOMP

# Local modules
from bc_coupling import BCCouplingBuilder
from geometry.geo_comps import GeoLink
from geometry.geo_vars import geo_vars
from propulsion.propulsion_group import PoddedFanBuilder
from utils.point_specs import AREA_REF, CHORD_REF, DV_UNITS, get_point_specs

# --- Get MPI info ---
COMM = MPI.COMM_WORLD
RANK = COMM.rank


class Top(Multipoint):
    def initialize(self):
        self.options.declare("model", default="bc", values=["az", "bc"], desc="Model type, either az or bc")
        self.options.declare("output_dir", default="./OUTPUT", types=str, desc="Output directory")
        self.options.declare("input_dir", default="./INPUT", types=str, desc="Input directory")
        self.options.declare("level", default="L2", values=["L0", "L0.5", "L1", "L1.5", "L2"], desc="Mesh level")
        self.options.declare("multiblock", default=False, types=bool, desc="Flag to use multiblock meshes.")
        self.options.declare("debug", default=False, types=bool, desc="Flag to run in debugging mode.")
        self.options.declare(
            "feedfwd", default=False, types=bool, desc="Flag to use feed-forward coupling.  Only works for az version"
        )
        self.options.declare(
            "target_net_thrust", default=6000, desc="Target net thrust"
        )

    def setup(self):
        # --- Read in the options ---
        model = self.options["model"]
        output_dir = self.options["output_dir"]
        input_dir = self.options["input_dir"]
        level = self.options["level"]
        mb = self.options["multiblock"]
        feedfwd = self.options["feedfwd"]

        # Set some useful vars based on the options
        self.mb_mesh = "_mb" if mb else ""

        # --- Get the inital values ---
        self.init_values = get_point_specs(feedfwd=feedfwd)

        ##############################
        # Aero
        ##############################
        # Set the grid file
        grid_file = os.path.join(input_dir, "volume_mesh", f"pod{self.mb_mesh}_v2_{model}_vol_{level}.cgns")

        # Default ADflow options
        aero_options = {
            # Common Parameters
            "gridfile": grid_file,
            "outputDirectory": output_dir,
            "solutionPrecision": "double",
            "liftindex": 3,
            "monitorvariables": ["resrho", "resturb", "cl", "cd", "cpu", "yplus"],
            "volumevariables": ["resrho", "blank", "resturb", "mach", "temp"],
            "surfacevariables": ["vx", "vy", "vz", "blank", "cp", "mach", "sepsensor", "p", "temp", "ptloss"],
            "isoSurface": {"shock": 1, "vx": -0.0001},
            "writevolumesolution": False,
            "writesurfacesolution": True,
            "writetecplotsurfacesolution": False,
            # Physics Parameters
            "equationType": "RANS",
            "smoother": "DADI",
            "MGCycle": "sg",
            "MGStartLevel": -1,
            # ANK Solver Parameters
            "useANKSolver": True,
            "ankswitchtol": 100.0,  # increase the switchtol from 1 to a high number because some iterations slightly go above the original residual and it kicks into dadi...
            "nsubiterturb": 7,
            "anksecondordswitchtol": 1e-4,
            "ankinnerpreconits": 2,
            "ankouterpreconits": 2,
            "ankpcilufill": 2,
            "ankasmoverlap": 2,
            "anklinresmax": 0.1,
            "infchangecorrection": True,
            "ankcfllimit": 1e4,
            # 'ankmaxiter': 1,
            # 'ankuseturbdadi':False,
            # 'ankturbkspdebug':True,
            # NK
            "usenksolver": False,
            "nkswitchtol": 1e-8,
            "nkadpc": True,
            "nkjacobianlag": 5,
            "nkouterpreconits": 3,
            "nkinnerpreconits": 2,
            # Convergence Parameters
            "L2Convergence": 1e-12,
            "adjointl2convergence": 1e-12,
            # ADjoint paramers
            "adjointl2convergencerel":1e-12,
            "adjointsubspacesize": 300,
            "adjointmaxiter": 300,
            "innerpreconits": 2,
            "adpc": True,
            "ilufill": 3,
            "outerpreconits": 4,
            # Overset parameters
            "usezippermesh": True,
            "nearwalldist": {"L2": 0.003, "L1.5": 0.002, "L1": 0.0015, "L0.5": 0.001, "L0": 0.00075}[level],
            # make sure all of the outer nacelle mesh is used instead of the background mesh
            "oversetpriority": {f"nacelle_vol_{level}.00003": 0.5, f"nacelle_vol_{level}.00006": 0.5},
        }

        # Set some ADflow options based on the model options
        aero_options["nCycles"] = {"az": 2000, "bc": 10000}[model]
        aero_options["ankcoupledswitchtol"] = {"az": 1e-16, "bc": 1e-5}[model]
        aero_options["L2ConvergenceRel"] = {"az": 1e-4, "bc": 1e-16}[model]
        aero_options["adjointl2convergencerel"] = {"az": 1e-4, "bc": 1e-16}[model]
        aero_options["asmoverlap"] = 2 if level == "L1" else 1

        # Mesh options for IDWarp
        mesh_options = {"gridFile": grid_file, "LdefFact":15.0}

        # Create the Aero Builder
        self.aero_builder = ADflowBuilder(
            options=aero_options,
            mesh_options=mesh_options,
            scenario="aeropropulsive",
            err_on_convergence_fail={"az": False, "bc": True}[model],
            restart_failed_analysis={"az": False, "bc": True}[model],
        )
        self.aero_builder.initialize(self.comm)

        ##############################
        # Propulsion
        ##############################
        prop_builder = PoddedFanBuilder(fan_model=model, outdir=output_dir)
        prop_builder.initialize(self.comm)

        ##############################
        # BC Coupling
        ##############################
        bc_coupling_builder = BCCouplingBuilder() if model == "bc" else None

        ##############################
        # Mphys
        ##############################
        # Add IVC's for design variables of different disciplines
        self.add_subsystem("aero_dvs", om.IndepVarComp())
        self.add_subsystem("geo_dvs", om.IndepVarComp())

        ##############################
        # Geometry
        ##############################
        # Add the geometry linking component
        self.add_subsystem("geo_link", GeoLink())

        # Add the mesh component
        self.add_subsystem("mesh", self.aero_builder.get_mesh_coordinate_subsystem())

        # Geometry with VSP
        self.add_subsystem(
            "geo",
            OM_DVGEOCOMP(
                file=os.path.join(input_dir, "pod_v2.vsp3"),
                type="vsp",
                options={"scale": 0.0254, "comps": ["Nacelle", "Core"], "projTol": 0.01},
            ),
        )

        # Add Scenario for cruise0 point
        self.mphys_add_scenario(
            "cruise0",
            ScenarioAeropropulsive(
                aero_builder=self.aero_builder, prop_builder=prop_builder, balance_builder=bc_coupling_builder
            ),
        )

    def configure(self):
        # --- Read in the options ---
        model = self.options["model"]
        output_dir = self.options["output_dir"]
        input_dir = self.options["input_dir"]
        level = self.options["level"]
        debug = self.options["debug"]
        target_net_thrust = self.options["target_net_thrust"]
        feedfwd = self.options["feedfwd"]

        ##############################
        # CFD Config
        ##############################
        # --- Get the CFD Solver from the aero builder ---
        CFDSolver = self.aero_builder.solver

        # --- Actuator Zone ---
        if model == "az":
            az_file = os.path.join(input_dir, "actuator_zone", f"actuator_{level}.xyz")
            axis1 = np.array([0, 0, 0])
            axis2 = np.array([1, 0, 0])
            CFDSolver.addActuatorRegion(az_file, axis1, axis2, "actuator_region", thrust=10000.0, torque=0.0, heat=0.0)

        # --- Add integration surfaces ---
        surfs = []

        # Names need to be different for fan face and fan exit int surfs
        # depending on the fan model.  This is due to the difference in
        # the BC and AZ mesh.
        fan_face_name = "fan_face" if model == "az" else "fan_face_mysurf"
        fan_exit_name = "fan_exit" if model == "az" else "fan_exit_mysurf"
        # These are added for both the AZ and BC versions
        # Fan face
        CFDSolver.addIntegrationSurface(
            os.path.join(input_dir, "integration_surfaces", f"fan_face_{level}_R2.xyz"), fan_face_name
        )
        surfs.append(fan_face_name)

        # Fan exit
        CFDSolver.addIntegrationSurface(
            os.path.join(input_dir, "integration_surfaces", f"fan_exit_{level}_R2.xyz"), fan_exit_name
        )
        surfs.append(fan_exit_name)

        # Inlet
        CFDSolver.addIntegrationSurface(os.path.join(input_dir, "integration_surfaces", f"inlet_{level}.xyz"), "inlet")
        surfs.append("inlet")

        # Nozzle
        CFDSolver.addIntegrationSurface(
            os.path.join(input_dir, "integration_surfaces", f"nozzle_{level}.xyz"), "nozzle"
        )
        surfs.append("nozzle")


        if model == "bc":
            surfs.append("fan_face")
            surfs.append("fan_exit")

        # --- Finalize the integration surfaces ---
        CFDSolver.finalizeUserIntegrationSurfaces()

        # --- Add functions to the surfaces ---
        funcs = [
            "mdot",
            "mavgptot",
            "aavgptot",
            "mavgttot",
            "mavgps",
            "aavgps",
            "mavgmn",
            "forcexpressure",
            "forcexmomentum",
            "forcexviscous",
            "area",
            "mavgvx",
            "mavgvy",
            "mavgvz",
            "fx",
            "fy",
            "fz",
        ]

        # Create a list to store the full function names after we add them
        # to ADflow.  These are functions that will be computed within
        # the coupling loop.
        coupling_funcs = []
        for surf in surfs:
            for func in funcs:
                if RANK == 0 and debug:
                    print(f"Adding ADflow function: {func} to family: {surf}")
                coupling_funcs.append(CFDSolver.addFunction(func, surf))

        # Define wall drag for performance calculations
        # This uses the auto-generated 'wall' family
        coupling_funcs.append(CFDSolver.addFunction("drag", "wall"))

        # Add the az flowpower
        if model == "az":
            coupling_funcs.append(CFDSolver.addFunction("flowpower", "actuator_region"))

        # Add integrated drag other forces
        coupling_funcs.extend(["drag", "fx", "fy", "fz", "cfx"])

        # Sort the funcs to get them in alphabetical order
        coupling_funcs.sort()

        # Create a list to store function names for functions that are
        # computed in the aero_post group
        aero_post_funcs = ["cl", "cd", "drag"]

        ##############################
        # Scenario Config
        ##############################
        # Get the scenario group cruise0 point
        scenario = getattr(self, "cruise0")

        # Create the aero problem
        ap = AeroProblem(
            name=f"cruise0{self.mb_mesh}_{model}",
            alpha=self.init_values.alpha["cruise0"],
            mach=self.init_values.mach["cruise0"],
            altitude=self.init_values.altitude["cruise0"],
            areaRef=AREA_REF,
            chordRef=CHORD_REF,
            evalFuncs=sorted(aero_post_funcs.copy()),
        )

        # Add DV's common to both models
        ap.addDV("alpha", value=self.init_values.alpha["cruise0"], name="alpha", units=DV_UNITS["alpha"])
        ap.addDV("mach", value=self.init_values.mach["cruise0"], name="mach", units=DV_UNITS["mach"])
        ap.addDV("altitude", value=self.init_values.altitude["cruise0"], name="altitude", units=DV_UNITS["altitude"])

        # Actuator zone DVs
        if model == "az":
            ap.setBCVar("Thrust", self.init_values.thrust0["cruise0"], "actuator_region")
            ap.addDV("Thrust", family="actuator_region", units=DV_UNITS["thrust"], name="thrust")

            ap.setBCVar("Heat", self.init_values.heat0["cruise0"], "actuator_region")
            ap.addDV("Heat", family="actuator_region", units=DV_UNITS["heat"], name="heat")

        # Boundary condition DVs
        else:
            ap.setBCVar("Pressure", self.init_values.Ps0["cruise0"], "fan_face")
            ap.addDV("Pressure", family="fan_face", units=DV_UNITS["Ps"], name="Ps")

            ap.setBCVar("PressureStagnation", self.init_values.Ptot0["cruise0"], "fan_exit")
            ap.addDV("PressureStagnation", family="fan_exit", units=DV_UNITS["Ptot"], name="Ptot")

            ap.setBCVar("TemperatureStagnation", self.init_values.Ttot0["cruise0"], "fan_exit")
            ap.addDV("TemperatureStagnation", family="fan_exit", units=DV_UNITS["Ttot"], name="Ttot")

        # Set the aeroproblem for the groups in the scenario
        scenario.coupling.aero.mphys_set_ap(ap)
        scenario.aero_post.mphys_set_ap(ap)

        # Add the DVs that are common to both model versions to the
        # aero dvs IVC
        for key in ["alpha", "mach", "altitude"]:
            # Set the name, value, and units for this variable
            dv_name = f"{key}_cruise0"
            dv_value = ap.DVs[key].value
            units = DV_UNITS[key]

            # Add the DV to the IVC
            self.aero_dvs.add_output(dv_name, val=dv_value, units=units)
            # Connect the IVC to the coupling and aero post groups
            self.connect(f"aero_dvs.{dv_name}", [f"cruise0.coupling.aero.{key}", f"cruise0.aero_post.{key}"])

        # Add the thrust for both fan models
        self.aero_dvs.add_output(f"thrust_cruise0", val=self.init_values.thrust0["cruise0"], units=DV_UNITS["thrust"])
        if model=='bc':
            self.aero_dvs.add_output(f"target_net_thrust_cruise0", val=target_net_thrust, units=DV_UNITS["thrust"])
        # Add/connect model specific IVC variables
        if model == "az":
            self.connect(
                "aero_dvs.thrust_cruise0",
                [
                    "cruise0.coupling.aero.thrust",
                    "cruise0.aero_post.thrust",
                    "cruise0.coupling.prop.aero:half_fan_thrust",
                ],
            )

        else:
            # we are doing a BC version so fan thrust connects to the balance group
            self.connect("aero_dvs.thrust_cruise0", ["cruise0.coupling.prop.aero:half_fan_thrust"])

            for key in ["Ps", "Ptot", "Ttot"]:
                # Set the name, value, and units for this variable
                dv_name = f"{key}_cruise0"
                dv_val = ap.DVs[key].value
                units = DV_UNITS[key]
                self.aero_dvs.add_output(dv_name, val=dv_val, units=units)

                self.connect(f"aero_dvs.{dv_name}", [f"cruise0.coupling.aero.{key}", f"cruise0.aero_post.{key}"])

            # Make connections from ADflow functionals to the BC coupling component
            aero_to_bc_connections = {
                "aavgps_fan_exit": "aero:P_stat:fan_exit",
                "aavgps_fan_face": "aero:P_stat:fan_face",
                "mavgvx_fan_exit": "aero:V:fan_exit",
                "mavgvx_fan_face": "aero:V:fan_face",
                "mavgttot_fan_exit": "aero:T_tot:fan_exit",
                "mavgttot_fan_face": "aero:T_tot:fan_face",
                "aavgptot_fan_exit": "aero:P_tot:fan_exit",
            }

            full_body_to_bc_conns = {
                "aero:mdot:fan_exit": "aero:mdot:fan_exit",
                "aero:mdot:fan_face": "aero:mdot:fan_face",
                "aero:area:fan_exit": "aero:area:fan_exit",
                "aero:area:fan_face": "aero:area:fan_face",
            }

            for key, val in aero_to_bc_connections.items():
                self.connect(f"cruise0.coupling.aero.{key}", f"cruise0.coupling.balance.{val}")

            for key, val in full_body_to_bc_conns.items():
                self.connect(f"cruise0.coupling.prop.{key}", f"cruise0.coupling.balance.{val}")

            # Add fan exit Mach to the IVC
            fan_mach = "fan_exit_mach_cruise0"
            self.aero_dvs.add_output(fan_mach, val=0.5, units=None)
            self.connect(f"aero_dvs.{fan_mach}", ["cruise0.coupling.prop.fan.MN"])

        # Add all of the functions for the coupling group
        scenario.coupling.aero.mphys_add_prop_funcs(coupling_funcs)

        ##############################
        # Aeropropulsive Configuration
        ##############################

        # Make aeropropulsive connections for the actuator zone version
        if model == "az":
            if not feedfwd:
                prop_to_aero_conn = {"aero:half_delta_heat": "heat"}
                self.connect("cruise0.coupling.prop.aero:half_delta_heat", "cruise0.aero_post.heat")
            else:
                scenario.coupling.aero.set_input_defaults("heat", val=0.0)
                prop_to_aero_conn = {}

        # Make aeropropulsive connections for the boundary condition version
        else:
            prop_to_aero_conn = {}  # No feedback in BC version
            prop_to_bc_conns = {
                "fan.Fl_O:stat:P": "prop:P_stat:fan_exit",
                "fan.Fl_O:tot:P": "prop:P_tot:fan_exit",
                "fan.Fl_O:tot:T": "prop:T_tot:fan_exit",
                "fan.Fl_O:stat:P": "prop:P_stat:fan_exit",
                "fan.Fl_O:stat:area": "prop:area:fan_exit",
                "fan.Fl_O:stat:V": "prop:V:fan_exit",
                "fan.Fl_O:stat:W": "prop:mdot:fan_exit",
                "prop:shaft_power": "prop:shaft_power",
            }

            for key, val in prop_to_bc_conns.items():
                self.connect(f"cruise0.coupling.prop.{key}", f"cruise0.coupling.balance.{val}")

        # Connections from aero to propulsion
        aero_to_prop_conn = {
            "aavgptot_fan_face": "aero:P_tot:fan_face",
            "aavgptot_fan_exit": "aero:P_tot:fan_exit",
            "aavgps_fan_face": "aero:P_stat:fan_face",
            "area_fan_face": "aero:half_area:fan_face",  # half
            "area_fan_exit": "aero:half_area:fan_exit",  # half
            "mdot_fan_exit": "aero:half_mdot:fan_exit",  # half
            "mdot_fan_face": "aero:half_mdot:fan_face",  # half
            "mavgvx_fan_face": "aero:V:fan_face",
            "drag_wall": "aero:half_drag",  # half
        }

        if model == "az":
            # save the actuator power as AZ power
            aero_to_prop_conn["flowpower_actuator_region"] = "aero:half_fan_power"  # half

        for key, val in prop_to_aero_conn.items():
            self.connect(f"cruise0.coupling.prop.{key}", f"cruise0.coupling.aero.{val}")

        for key, val in aero_to_prop_conn.items():
            self.connect(f"cruise0.coupling.aero.{key}", f"cruise0.coupling.prop.{val}")

        if model=="bc":
            self.connect("cruise0.coupling.aero.drag_wall", "cruise0.coupling.balance.aero:half_drag")
            self.connect("aero_dvs.target_net_thrust_cruise0", "cruise0.coupling.balance.target_net_thrust")

        ##############################
        # Geometry Configuration
        ##############################
        # create geometric DV setup
        coords = self.mesh.mphys_get_surface_mesh()

        # add pointset
        self.geo.nom_add_discipline_coords("aero", coords)

        # create constraint DV setup
        tri_points = self.mesh.mphys_get_triangulated_surface()
        self.geo.nom_setConstraintSurface(tri_points)

        # add DVs on the geo comp
        geoComp = self.geo
        for var in geo_vars:
            geoComp.nom_addVSPVariable(var.comp, var.group, var.var, scaledStep=False, dh=var.dh)

        # this brings in all the names and values of the DVs
        xdv = self.geo.DVGeos["defaultDVGeo"].getValues()

        # connect dvs to the ivc (with initial values)
        for key, val in xdv.items():
            # omit the two cross sections we set with an exec comp
            if key not in ["Nacelle:XSecCurve_8:Circle_Diameter", "Nacelle:XSecCurve_2:Circle_Diameter"]:
                self.geo_dvs.add_output(key, val=val)
                self.connect(f"geo_dvs.{key}", f"geo.{key}")

        # connect the advanced linking stuff separately
        self.connect("geo_dvs.Nacelle:XSecCurve_0:Circle_Diameter", "geo_link.XSecCurve_0")
        self.connect("geo_dvs.Nacelle:XSecCurve_1:Circle_Diameter", "geo_link.XSecCurve_1")
        self.connect("geo_link.XSecCurve_8", "geo.Nacelle:XSecCurve_8:Circle_Diameter")
        self.connect("geo_link.XSecCurve_2", "geo.Nacelle:XSecCurve_2:Circle_Diameter")

        # connect the mesh coordinates
        self.connect("mesh.x_aero0", "geo.x_aero_in")
        self.connect("geo.x_aero0", "cruise0.x_aero")

        ################################################################################
        # THICKNESS CONSTRAINTS
        ################################################################################

        # projection normal for the upper location
        normal = [0.0, 0.0, 1.0]
        # we do the full upper nacelle for this
        pt1 = [-0.17, 0.01, 1.05]
        pt2 = [2.11, 0.01, 0.86]
        geoComp.nom_addThicknessConstraints1D(
            "upper_thickness",
            np.vstack([pt1, pt2]),
            10,
            normal,
        )

        # projection normal for the outer location
        normal = [0.0, 1.0, 0.0]
        # only do fwd of the fan for the right side
        # rest of the sections are circular
        pt1 = [-0.17, 0.95, 0.0]
        pt2 = [0.59, 0.95, 0.0]
        geoComp.nom_addThicknessConstraints1D(
            "right_thickness",
            np.vstack([pt1, pt2]),
            4,
            normal,
        )

        # write constraints to a file
        if self.comm.rank == 0:
            file_name = os.path.join(output_dir, "thickness_constraints.dat")
            print(f"Writing constraints to file: {file_name}")
            self.geo.DVCon.writeTecplot(file_name)

        ################################################################################
        # SOLVER OPTIONS
        ################################################################################

        # get the scenario group
        scenario = getattr(self, "cruise0")

        if model == "az" and not feedfwd:
            # the actuator zone does a NLBGS iteartion until CFD and prop agree
            scenario.coupling.nonlinear_solver = om.NonlinearBlockGS(
                maxiter=10,
                use_apply_nonlinear=False,
                err_on_non_converge=True,
                atol=1e-2,
                rtol=1e-20,
            )
            scenario.coupling.linear_solver = om.LinearBlockGS(
                maxiter=4,
                atol=1e-20,
                rtol=1e-10,
            )

        else:
            # the BC version currently on consistency constraints
            scenario.coupling.nonlinear_solver = om.NonlinearRunOnce()
            scenario.coupling.linear_solver = om.LinearRunOnce()

        scenario.coupling.set_solver_print(level=2)
        scenario.coupling.prop.podded_fan.set_solver_print(level=-1)
        scenario.coupling.prop.podded_fan.set_solver_print(level=2, depth=1)
        scenario.coupling.linear_solver.options["iprint"] = 2