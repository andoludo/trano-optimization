"""The building blocks: translation, roles, collocation, simulation against known solutions, closed loop prices."""

import numpy as np
import pytest

from tests.test_optimization import HOUSE
from trano_optimization import (
    CasadiModel,
    CollocationSettings,
    OptimalControl,
    OptimalControlSettings,
    Roles,
    default_ipopt_options,
    linear_solver,
    receding_horizon,
)
from trano_optimization.collocation import Collocated, collocation_matrices

DECAY = """
package Decay
  connector RealInput = input Real;
  model Tank "First order system: x relaxes towards u/k"
    RealInput u "Inflow";
    parameter Real k = 2e-4 "Rate";
    Real x(start=10, fixed=true) "Level";
    Real E(start=0, fixed=true, unit="kWh") "Production meter";
  equation
    der(x) = u - k*x;
    der(E) = 0;
  end Tank;
end Decay;
"""
ARRAY = """
package Arrays
  connector RealInput = input Real;
  model Two
    RealInput u[2] "Two inputs";
    Real x(start=0, fixed=true);
  equation
    der(x) = u[1] - 2*u[2];
  end Two;
end Arrays;
"""


@pytest.fixture(scope="module")
def tank() -> CasadiModel:
    return CasadiModel.from_modelica(DECAY, "Decay.Tank")


def test_the_derivatives_are_those_of_the_equations(tank: CasadiModel) -> None:
    derivatives = tank.derivatives(0.0, np.array([10.0, 0.0]), np.array([0.5]))

    assert derivatives == pytest.approx([0.5 - 2e-4 * 10, 0.0])
    assert tank.derivatives(0.0, np.array([10.0, 0.0]), np.array([0.5]), np.array([1e-3])) == pytest.approx(
        [0.5 - 1e-2, 0.0]
    )


def test_array_inputs_are_named_element_by_element() -> None:
    model = CasadiModel.from_modelica(ARRAY, "Arrays.Two")

    assert model.description.input_names == ["u[1]", "u[2]"]
    assert model.derivatives(0.0, np.array([0.0]), np.array([3.0, 1.0])) == pytest.approx([1.0])


def test_the_simulation_follows_the_analytic_solution(tank: CasadiModel) -> None:
    """x' = u - k x: x(t) = u/k + (x0 - u/k) exp(-k t), with u held over each step."""
    roles = Roles(controls=(), disturbances=("u",), comfort=())
    simulator = Collocated(tank, roles=roles, settings=CollocationSettings(time_step=600))
    steps, u, k, x0 = 48, 1e-3, 2e-4, 10.0

    states = simulator.simulate(np.array([x0, 0.0]), np.zeros((0, steps)), np.full((1, steps), u))

    times = np.arange(steps + 1) * 600
    assert states.shape == (2, steps + 1)
    # CVODES runs at 1e-6 (absolute and relative) over each step
    np.testing.assert_allclose(states[0], u / k + (x0 - u / k) * np.exp(-k * times), rtol=1e-4)


def test_roles_cannot_make_an_input_both_a_control_and_a_disturbance() -> None:
    with pytest.raises(ValueError, match="both controls and disturbances"):
        Roles(controls=("u",), disturbances=("u",), comfort=())


def test_roles_are_checked_against_the_model(tank: CasadiModel) -> None:
    with pytest.raises(ValueError, match="Unknown variables"):
        Roles(controls=(), disturbances=("u", "v"), comfort=()).check(tank.description)
    with pytest.raises(ValueError, match="without a role"):
        Roles(controls=(), disturbances=(), comfort=()).check(tank.description)
    Roles(controls=(), disturbances=("u",), comfort=()).check(tank.description)


def test_meters_take_their_carrier_from_their_name(tank: CasadiModel) -> None:
    roles = Roles.infer(tank.description, comfort_pattern=r"^x$")

    assert roles.meters == {"E": "electricity"}  # neither EFue nor EPro: electricity
    assert roles.comfort == ("x",)
    assert roles.controls == ()
    assert roles.disturbances == ("u",)


@pytest.mark.parametrize("degree", [1, 2, 3, 5])
def test_the_collocation_matrices_are_exact_for_polynomials(degree: int) -> None:
    """D interpolates the end of the step, C differentiates: both exact for polynomials of the degree."""
    tau, c_matrix, d_vector = collocation_matrices(degree)

    assert len(tau) == degree + 1 and tau[0] == 0.0 and tau[-1] == pytest.approx(1.0)  # Radau: the end is a point
    assert sum(d_vector) == pytest.approx(1.0)
    for power in range(degree + 1):
        values = tau**power
        assert sum(d * v for d, v in zip(d_vector, values, strict=True)) == pytest.approx(1.0)
        for r in range(1, degree + 1):
            derivative = sum(c_matrix[j][r] * values[j] for j in range(degree + 1))
            assert derivative == pytest.approx(power * tau[r] ** (power - 1) if power else 0.0, abs=1e-9)


def test_the_solver_settings_merge_with_the_defaults() -> None:
    assert linear_solver() in {"spral", "mumps"}
    defaults = default_ipopt_options()
    assert defaults["linear_solver"] == linear_solver()

    options = CollocationSettings(ipopt={"max_iter": 5}).ipopt_options()

    assert options["max_iter"] == 5
    assert options["tol"] == defaults["tol"]


def test_the_closed_loop_charges_fuel_at_its_own_price() -> None:
    """Dear fuel moves the heating from the boiler to the ideal (electric) heater, which alone is too small."""
    room = CasadiModel.from_modelica(HOUSE, "House.Room")
    ocp = OptimalControl(room, settings=OptimalControlSettings(time_step=3600))
    steps, horizon = 3, 4
    total = steps + horizon
    disturbances = np.vstack([np.full(total, 273.15), np.zeros(total)])
    comfort = np.full(total, 273.15 + 20)
    price = np.full(total, 0.3)

    def boiler_and_heater(fuel: float) -> tuple[float, float]:
        result = receding_horizon(
            ocp, room.description.initial_state, disturbances, comfort, price, horizon, fuel_price=np.full(total, fuel)
        )
        assert all(status in {"Solve_Succeeded", "Solved_To_Acceptable_Level"} for status in result.statuses)
        boiler, heater = result.controls
        return float(boiler.sum()), float(heater.sum())

    cheap_boiler, cheap_heater = boiler_and_heater(0.01)
    dear_boiler, dear_heater = boiler_and_heater(10.0)

    assert cheap_boiler > dear_boiler
    assert dear_heater > cheap_heater
