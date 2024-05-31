# External modules
from mphys import Builder
import openmdao.api as om
from tabulate import tabulate

# Local modules
from .fan import PoddedFan
from .full_body import FullBody


class FanInletDebug(om.ExplicitComponent):
    def setup(self):
        self.add_input("aero:P_stat:fan_face", desc="Static pressure from CFD at the fan face", units="Pa")
        self.add_input("aero:P_tot:fan_face", desc="Total pressure from CFD at the fan face", units="Pa")
        self.add_input("aero:P_tot:fan_exit", desc="Total pressure from CFD at the fan exit", units="Pa")

        self.add_input("aero:half_area:fan_face", desc="Half-body area from CFD at the fan face", units="m**2")
        self.add_input("aero:area:fan_face", desc="Full-body area from CFD at the fan face", units="m**2")

        self.add_input(
            "aero:half_mdot:fan_face", desc="Half-body mass flow rate from CFD at the fan face", units="kg/s"
        )
        self.add_input("aero:mdot:fan_face", desc="Full-body mass flow rate from CFD at the fan face", units="kg/s")
        self.add_input(
            "aero:half_mdot:fan_exit", desc="Half-body mass flow rate from CFD at the fan exit", units="kg/s"
        )
        self.add_input("aero:mdot:fan_exit", desc="Full-body mass flow rate from CFD at the fan exit", units="kg/s")

        self.add_input("aero:V:fan_face", desc="Static velocity from CFD at the fan face", units="m/s")

        self.add_output("foo")

    def compute(self, inputs, outputs):
        outputs["foo"] = 1.0
        if self.comm.rank == 0:
            print("\n*******************************", flush=True)
            print("***     FAN INLET DEBUG     ***", flush=True)
            print("*******************************", flush=True)

            meta = self._var_abs2meta["input"]
            table = [[key.split(".")[-1], val[0], meta["cruise0.coupling.prop.fan_inlet_debug."+key]["units"]] for key, val in inputs.items()]
            headers = ["Name", "Value", "Units"]
            print(
                tabulate(
                    table,
                    headers=headers,
                    colalign=("right", "left", "left"),
                    floatfmt=".4f",
                )
            )

            print("*******************************\n", flush=True)


class FanPowerDebug(om.ExplicitComponent):
    def setup(self):
        self.add_input(
            "prop:delta_heat",
            desc="Energy lost as heat from fan efficiency losses",
            units="kW",
        )
        self.add_input("aero:fan_power", desc="Full-body fan power from CFD", units="kW")
        self.add_input("prop:shaft_power", desc="Shaft power computed in pyCycle", units="kW")

        self.add_input("total_shaft_power", desc="Total shaft power for the fan", units="kW")
        self.add_input(
            "aero:half_delta_heat",
            desc="Half-body fan efficiency losse due to heat",
            units="kW",
        )

        self.add_output("foo")

    def compute(self, inputs, outputs):
        outputs["foo"] = 1.0
        if self.comm.rank == 0:
            print("\n*******************************", flush=True)
            print("***     FAN POWER DEBUG     ***", flush=True)
            print("*******************************", flush=True)

            meta = self._var_abs2meta["input"]
            table = [[key.split(".")[-1], val[0], meta["cruise0.coupling.prop.power_debug."+key]["units"]] for key, val in inputs.items()]
            headers = ["Name", "Value", "Units"]
            print(tabulate(table, headers=headers, colalign=("right", "left", "left"), floatfmt=".4f"))

            print("*******************************\n", flush=True)


class FanPerfDebug(om.ExplicitComponent):
    def setup(self):

        self.add_input(
            "aero:half_fan_thrust",
            desc="Half-body actuator zone thrust from CFD",
            units="N",
        )
        self.add_input("aero:half_drag", desc="Half-body wall drag from CFD", units="N")

        self.add_input("Fn", desc="Installed net thrust of the podded fan", units="N")
        self.add_input("FPR", desc="FPR")
        
        self.add_output("foo")

    def compute(self, inputs, outputs):
        outputs["foo"] = 1.0
        if self.comm.rank == 0:
            print("\n********************************", flush=True)
            print("***      FAN PERF DEBUG      ***", flush=True)
            print("********************************", flush=True)

            meta = self._var_abs2meta["input"]
            table = [[key.split(".")[-1], val[0], meta["cruise0.coupling.prop.perf_debug."+key]["units"]] for key, val in inputs.items()]
            headers = ["Name", "Value", "Units"]
            print(
                tabulate(
                    table,
                    headers=headers,
                    colalign=("right", "left", "left"),
                    floatfmt=".4f",
                )
            )

            print("*******************************\n", flush=True)


class NetThrust(om.ExplicitComponent):
    def setup(self):
        self.add_input("aero:half_fan_thrust", desc="Half-body fan thrust from CFD", units="N")
        self.add_input("aero:half_drag", desc="Half-body wall drag from CFD", units="N")

        self.add_output("Fn", desc="Installed net thrust of the podded fan", units="N")

        self.declare_partials("Fn", ["aero:half_fan_thrust", "aero:half_drag"])

    def compute(self, inputs, outputs):
        outputs["Fn"] = inputs["aero:half_fan_thrust"] - inputs["aero:half_drag"]

    def compute_partials(self, inputs, partials):
        partials["Fn", "aero:half_drag"] = -1.0
        partials["Fn", "aero:half_fan_thrust"] = 1.0


class TotalPower(om.ExplicitComponent):

    def setup(self):

        self.add_input(
            "prop:delta_heat",
            desc="Energy lost as heat from fan efficiency losses",
            units="kW",
        )
        self.add_input("aero:fan_power", desc="Full-body fan power from CFD", units="kW")

        self.add_output("total_shaft_power", desc="Total shaft power for the fan", units="kW")
        self.add_output(
            "aero:half_delta_heat",
            desc="Half-body fan efficiency losse due to heat",
            units="kW",
        )

        self.declare_partials("total_shaft_power", ["aero:fan_power", "prop:delta_heat"])
        self.declare_partials("aero:half_delta_heat", "prop:delta_heat")


    def compute(self, inputs, outputs):
        outputs["total_shaft_power"] = inputs["aero:fan_power"] + inputs["prop:delta_heat"]
        outputs["aero:half_delta_heat"] = 0.5 * inputs["prop:delta_heat"]

    def compute_partials(self, inputs, partials):
        partials["total_shaft_power", "aero:fan_power"] = 1.0
        partials["total_shaft_power", "prop:delta_heat"] = 1.0
        partials["aero:half_delta_heat", "prop:delta_heat"] =  0.5


class PropulsionGroup(om.Group):
    def initialize(self):
        self.options.declare("design", default=True)
        self.options.declare("fan_model", default="az")

    def setup(self):
        fan_model = self.options["fan_model"]
        design = self.options["design"]
        # Add the subsystems
        self.add_subsystem("full_body", FullBody(), promotes=["*"])
        self.add_subsystem("fan_inlet_debug", FanInletDebug(), promotes_inputs=["*"])
        self.add_subsystem("podded_fan", PoddedFan(design=design), promotes=["*"])
        self.add_subsystem("net_thrust", NetThrust(), promotes=["*"])
        self.add_subsystem("total_power", TotalPower(), promotes=["*"])
        self.add_subsystem("perf_debug", FanPerfDebug(), promotes_inputs=["*"])
        self.add_subsystem("power_debug", FanPowerDebug(), promotes_inputs=["*"])


class PoddedFanBuilder(Builder):
    def __init__(self, fan_model="az", outdir="./", design=True):
        
        self.fan_model = fan_model
        self.outdir = outdir
        self.design = design

    def get_coupling_group_subsystem(self, scenario_name=None):
        coupling_group = PropulsionGroup(fan_model=self.fan_model, design=self.design)
        return coupling_group
    

