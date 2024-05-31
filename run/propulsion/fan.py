# External modules
import openmdao.api as om
import pycycle.api as pyc

# Local modules
from .n3_fan_map import FanMap


class FPR(om.ExplicitComponent):
    def setup(self):
        self.add_input("aero:P_tot:fan_face", desc="Total pressure at the fan face", units="Pa")
        self.add_input("aero:P_tot:fan_exit", desc="Total pressure at the fan exit", units="Pa")

        self.add_output("FPR", desc="Fan pressure ratio")

        self.declare_partials("*", "*")

    def compute(self, inputs, outputs):
        outputs["FPR"] = inputs["aero:P_tot:fan_exit"] / inputs["aero:P_tot:fan_face"]

    def compute_partials(self, inputs, partials):
        partials["FPR", "aero:P_tot:fan_face"] = -inputs["aero:P_tot:fan_exit"] / (inputs["aero:P_tot:fan_face"] ** 2)
        partials["FPR", "aero:P_tot:fan_exit"] = 1.0 / inputs["aero:P_tot:fan_face"]


class FanPerformance(om.ExplicitComponent):
    def setup(self):
        self.add_input("aero:mdot:fan_face", desc="Mass flow rate from CFD at the fan face", units="kg/s")
        self.add_input("prop:h_real", desc="Real enthalpy from the pyCycle fan", units="kJ/kg")
        self.add_input("prop:h_ideal", desc="Ideal enthalpy from the pyCycle fan", units="kJ/kg")
        self.add_input("prop:fan_power", desc="Fan power from pyCycle", units="kW")

        self.add_output("prop:shaft_power", desc="Shaft power output", units="kW")
        self.add_output("prop:delta_heat", desc="Energy lost as heat from fan efficiency losses", units="kW")

        self.declare_partials("prop:shaft_power", "prop:fan_power")
        self.declare_partials("prop:delta_heat", ["aero:mdot:fan_face", "prop:h_real", "prop:h_ideal"])

    def compute(self, inputs, outputs):
        outputs["prop:shaft_power"] = -inputs["prop:fan_power"]
        outputs["prop:delta_heat"] = inputs["aero:mdot:fan_face"] * (inputs["prop:h_real"] - inputs["prop:h_ideal"])

    def compute_partials(self, inputs, partials):
        partials["prop:shaft_power", "prop:fan_power"] = -1.0
        partials["prop:delta_heat", "aero:mdot:fan_face"] = 1.0 * (inputs["prop:h_real"] - inputs["prop:h_ideal"])
        partials["prop:delta_heat", "prop:h_real"] = inputs["aero:mdot:fan_face"]
        partials["prop:delta_heat", "prop:h_ideal"] = -inputs["aero:mdot:fan_face"]


class PoddedFan(pyc.Cycle):
    def setup(self):
        design = self.options["design"]

        self.add_subsystem(
            "cfd_start",
            pyc.CFDStart(),
            promotes_inputs=[
                ("Ps", "aero:P_stat:fan_face"),
                ("W", "aero:mdot:fan_face"),
                ("area", "aero:area:fan_face"),
                ("V", "aero:V:fan_face"),
            ],
        )
        self.add_subsystem("fpr", FPR(), promotes_inputs=["*"], promotes_outputs=["*"])
        self.add_subsystem("fan", pyc.Compressor(map_data=FanMap, design=design, map_extrap=True))
        self.add_subsystem(
            "perf",
            FanPerformance(),
            promotes_inputs=["aero:mdot:fan_face"],
            promotes_outputs=["prop:delta_heat", "prop:shaft_power"],
        )

        self.pyc_connect_flow("cfd_start.Fl_O", "fan.Fl_I")

        balance = self.add_subsystem("balance", om.BalanceComp())

        balance.add_balance("fan_eta_a", lower=0.7, upper=0.999, rhs_val=0.97)
        self.connect("balance.fan_eta_a", "fan.eff")
        self.connect("fan.eff_poly", "balance.lhs:fan_eta_a")

        self.connect("FPR", "fan.PR")

        self.connect("fan.power", "perf.prop:fan_power")
        self.connect("fan.enth_rise.ht_out", "perf.prop:h_real")
        self.connect("fan.ideal_flow.h", "perf.prop:h_ideal")

        newton = self.nonlinear_solver = om.NewtonSolver()
        newton.options["atol"] = 1e-10
        newton.options["rtol"] = 1e-10
        newton.options["iprint"] = 2
        newton.options["maxiter"] = 15
        newton.options["solve_subsystems"] = True
        newton.options["max_sub_solves"] = 25
        newton.options["err_on_non_converge"] = True
        newton.options["restart_from_successful"] = True

        self.linear_solver = om.DirectSolver()

        super().setup()
