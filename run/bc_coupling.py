# External modules
from mphys.builder import Builder
import openmdao.api as om
from tabulate import tabulate


class BCCouplingDebug(om.ExplicitComponent):
    def setup(self):
        self.add_input("enr:fan_face", units="kW")
        self.add_input("enr:fan_exit", units="kW")

        self.add_input(
            "aero:P_stat:fan_exit", desc="Area averaged static pressure from CFD at the fan exit", units="Pa"
        )
        self.add_input("aero:V:fan_exit", desc="Mass averaged velocity from CFD at the fan exit", units="m/s")
        self.add_input("aero:V:fan_face", desc="Mass averaged velocity from CFD at the fan exit", units="m/s")
        self.add_input("aero:mdot:fan_exit", desc="Mass flow rate from CFD at the fan exit", units="kg/s")
        self.add_input("aero:area:fan_exit", desc="Integrated area from CFD at the fan exit", units="m**2")
        self.add_input("prop:P_stat:fan_exit", desc="Static pressure from pyCycle at the fan exit", units="Pa")
        self.add_input("prop:V:fan_exit", desc="Static velocity from pyCycle at the fan exit", units="m/s")
        self.add_input("prop:mdot:fan_exit", desc="Mass flow rate from pyCycle at the fan exit", units="kg/s")
        self.add_input("prop:area:fan_exit", desc="Area from pyCycle at the fan exit", units="m**2")
        self.add_input(
            "aero:P_stat:fan_face", desc="Area averaged static pressure from CFD at the fan exit", units="Pa"
        )
        self.add_input("aero:mdot:fan_face", desc="Mass flow rate from CFD at the fan exit", units="kg/s")
        self.add_input("aero:area:fan_face", desc="Integrated area from CFD at the fan exit", units="m**2")

        self.add_input("aero:half_drag", desc="Half-body fan thrust from CFD", units="N")
        self.add_input("target_net_thrust", desc="Half-body net fan thrust from CFD", units="N")

        self.add_input("aero:T_tot:fan_exit", desc="Static pressure from pyCycle at the fan exit", units="degK")
        self.add_input("aero:P_tot:fan_exit", desc="Static pressure from pyCycle at the fan exit", units="Pa")

        self.add_input("prop:T_tot:fan_exit", desc="Static pressure from pyCycle at the fan exit", units="degK")
        self.add_input("prop:P_tot:fan_exit", desc="Static pressure from pyCycle at the fan exit", units="Pa")

        self.add_input("res_P_tot", desc="Static pressure residual at the fan exit", units="Pa")
        self.add_input("res_T_tot", desc="Static velocity residual at the fan exit", units="degK")
        
        self.add_input("res_Ps", desc="Static pressure residual at the fan exit", units="Pa")
        self.add_input("res_V", desc="Static velocity residual at the fan exit", units="m/s")

        self.add_input("res_mdot", desc="Mass flow rate residual at the fan exit", units="kg/s")
        self.add_input("res_area", desc="Area residual at the fan exit", units="m**2")
        self.add_input("res_net_thrust", desc="Thrust residual", units="N")
        self.add_input("res_enr", desc="energy residual", units="kW")
        self.add_input("prop:shaft_power", units="kW")

        self.add_output("foo")

    def compute(self, inputs, outputs):
        outputs["foo"] = 1.0
        if self.comm.rank == 0:
            print("\n*****************************", flush=True)
            print("***     BC DEBUG OUTPUT     ***", flush=True)
            print("*******************************", flush=True)

            meta = self._var_abs2meta["input"]
            table = [[key.split(".")[-1], val[0], meta["cruise0.coupling.balance.debug_balance."+key]["units"]] for key, val in inputs.items()]
            headers = ["Name", "Value", "Units"]
            print(tabulate(table, headers=headers, colalign=("right", "left", "left"), floatfmt=".4f"))

            print("*******************************\n", flush=True)


class BCStaticsConservation(om.ExplicitComponent):
    def setup(self):
        self.add_input(
            "aero:P_stat:fan_exit", desc="Area averaged static pressure from CFD at the fan exit", units="Pa"
        )
        self.add_input(
            "aero:P_stat:fan_face", desc="Area averaged static pressure from CFD at the fan exit", units="Pa"
        )
        self.add_input("aero:V:fan_exit", desc="Mass averaged velocity from CFD at the fan exit", units="m/s")
        self.add_input("aero:V:fan_face", desc="Mass averaged velocity from CFD at the fan exit", units="m/s")
        self.add_input("aero:mdot:fan_exit", desc="Mass flow rate from CFD at the fan exit", units="kg/s")
        self.add_input("aero:mdot:fan_face", desc="Mass flow rate from CFD at the fan exit", units="kg/s")
        self.add_input("aero:area:fan_exit", desc="Integrated area from CFD at the fan exit", units="m**2")
        self.add_input("aero:area:fan_face", desc="Integrated area from CFD at the fan exit", units="m**2")
        self.add_input("aero:T_tot:fan_exit", desc="Static pressure from pyCycle at the fan exit", units="degK")
        self.add_input("aero:P_tot:fan_exit", desc="Static pressure from pyCycle at the fan exit", units="Pa")

        self.add_input("prop:P_stat:fan_exit", desc="Static pressure from pyCycle at the fan exit", units="Pa")
        self.add_input("prop:T_tot:fan_exit", desc="Static pressure from pyCycle at the fan exit", units="degK")
        self.add_input("prop:P_tot:fan_exit", desc="Static pressure from pyCycle at the fan exit", units="Pa")
        self.add_input("prop:V:fan_exit", desc="Static velocity from pyCycle at the fan exit", units="m/s")
        self.add_input("prop:mdot:fan_exit", desc="Mass flow rate from pyCycle at the fan exit", units="kg/s")
        self.add_input("prop:area:fan_exit", desc="Area from pyCycle at the fan exit", units="m**2")

        self.add_input("aero:half_drag", desc="Half-body fan thrust from CFD", units="N")
        self.add_input("target_net_thrust", desc="Half-body net fan thrust from CFD", units="N")

        self.add_output("res_Ps", desc="Static pressure residual at the fan exit", units="Pa")
        self.add_output("res_V", desc="Static velocity residual at the fan exit", units="m/s")
        self.add_output("res_mdot", desc="Mass flow rate residual at the fan exit", units="kg/s")
        self.add_output("res_area", desc="Area residual at the fan exit", units="m**2")
        self.add_output("res_net_thrust", desc="fan thrust", units="N")
        self.add_output("res_P_tot", desc="Static pressure residual at the fan exit", units="Pa")
        self.add_output("res_T_tot", desc="Static pressure residual at the fan exit", units="degK")

        self.declare_partials("res_P_tot", ["aero:P_tot:fan_exit", "prop:P_tot:fan_exit"], method="cs")
        self.declare_partials("res_T_tot", ["aero:T_tot:fan_exit", "prop:T_tot:fan_exit"], method="cs")

        self.declare_partials("res_Ps", ["aero:P_stat:fan_exit", "prop:P_stat:fan_exit"], method="cs")
        self.declare_partials("res_V", ["aero:V:fan_exit", "prop:V:fan_exit"], method="cs")
        self.declare_partials("res_mdot", ["aero:mdot:fan_exit", "prop:mdot:fan_exit"], method="cs")
        self.declare_partials("res_area", ["aero:area:fan_exit", "prop:area:fan_exit"], method="cs")
        self.declare_partials("res_net_thrust", ["aero:area:fan_exit","aero:area:fan_face", "aero:mdot:fan_face","aero:mdot:fan_exit","aero:V:fan_exit","aero:V:fan_face","aero:P_stat:fan_face","aero:P_stat:fan_exit","aero:half_drag","target_net_thrust"], method="cs")

    def compute(self, inputs, outputs):
        aero_P_out = inputs["aero:P_stat:fan_exit"]
        aero_V_out = inputs["aero:V:fan_exit"]
        aero_mdot_out = inputs["aero:mdot:fan_exit"]
        aero_area_out = inputs["aero:area:fan_exit"]
        prop_P_out = inputs["prop:P_stat:fan_exit"]
        prop_V_out = inputs["prop:V:fan_exit"]
        prop_mdot_out = inputs["prop:mdot:fan_exit"]
        prop_area_out = inputs["prop:area:fan_exit"]
        aero_mdot_in = inputs["aero:mdot:fan_face"]
        aero_area_in = inputs["aero:area:fan_face"]
        aero_V_in = inputs["aero:V:fan_face"]
        aero_P_in = inputs["aero:P_stat:fan_face"]

        aero_Ttot_out = inputs["aero:T_tot:fan_exit"]
        aero_Ptot_out = inputs["aero:P_tot:fan_exit"]
        prop_Ttot_out = inputs["prop:T_tot:fan_exit"]
        prop_Ptot_out = inputs["prop:P_tot:fan_exit"]

        aero_drag = inputs["aero:half_drag"]
        target_netthrust = inputs["target_net_thrust"]
        Thrust_fan =  (aero_mdot_out * aero_V_out + aero_P_out * aero_area_out) - (aero_mdot_in * aero_V_in + aero_P_in * aero_area_in)

        outputs["res_P_tot"] = aero_Ptot_out - prop_Ptot_out
        outputs["res_T_tot"] = aero_Ttot_out - prop_Ttot_out
        outputs["res_Ps"] = aero_P_out - prop_P_out
        outputs["res_V"] = aero_V_out - prop_V_out
        outputs["res_mdot"] = aero_mdot_out - prop_mdot_out
        outputs["res_area"] = aero_area_out - prop_area_out
        outputs["res_net_thrust"] = Thrust_fan - 2*aero_drag -2*target_netthrust


class BCEnergyConservation(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("Cp", default=1.0045, types=float, desc="Specific heat at constant pressure")

    def setup(self):
        self.add_input("prop:shaft_power", desc="Shaft power from pyCycle", units="kW")
        self.add_input("aero:mdot:fan_face", desc="Mass flow rate from CFD at the fan face", units="kg/s")
        self.add_input("aero:mdot:fan_exit", desc="Mass flow rate from CFD at the fan exit", units="kg/s")
        self.add_input("aero:T_tot:fan_face", desc="Total temperature from CFD at the fan face", units="degK")
        self.add_input("aero:T_tot:fan_exit", desc="Total temperature from CFD at the fan exit", units="degK")

        self.add_output("enr:fan_face", desc="Energy entering the control volume around the fan", units="kW")
        self.add_output("enr:fan_exit", desc="Energy leaving the control volume around the fan", units="kW")
        self.add_output("res_enr", desc="Energy residual", units="kW")

        self.declare_partials(
            "enr:fan_face", ["prop:shaft_power", "aero:mdot:fan_face", "aero:T_tot:fan_face"], method="cs"
        )
        self.declare_partials("enr:fan_exit", ["aero:mdot:fan_exit", "aero:T_tot:fan_exit"], method="cs")
        self.declare_partials("res_enr", "*", method="cs")

    def compute(self, inputs, outputs):
        shaft_power = inputs["prop:shaft_power"]
        mdot_in = inputs["aero:mdot:fan_face"]
        mdot_out = inputs["aero:mdot:fan_exit"]
        T_in = inputs["aero:T_tot:fan_face"]
        T_out = inputs["aero:T_tot:fan_exit"]

        # Shaft power comes from pyCycle and is for the full body, so we divide by 2
        outputs["enr:fan_face"] = 0.5 * shaft_power - mdot_in * T_in * self.options["Cp"]
        outputs["enr:fan_exit"] = mdot_out * T_out * self.options["Cp"]
        outputs["res_enr"] = outputs["enr:fan_face"] - outputs["enr:fan_exit"]


class BCCouplingGroup(om.Group):
    def setup(self):
        self.add_subsystem("energy_cons", BCEnergyConservation(), promotes=["*"])
        self.add_subsystem("static_cons", BCStaticsConservation(), promotes=["*"])
        self.add_subsystem("debug_balance", BCCouplingDebug(), promotes=["*"])


class BCCouplingBuilder(Builder):
    def __init__(self):
        pass

    def get_coupling_group_subsystem(self, scenario_name=None):
        return BCCouplingGroup()

    # def get_post_coupling_subsystem(self, scenario_name=None):
    #     return BCCouplingGroup()

    def initialize(self, comm):
        pass