# trano-optimization

Optimal control, moving horizon estimation and simulation of Modelica models: [rumoca](https://github.com/CogniPilot/rumoca)
translates the model into a CasADi function, solved by direct collocation with IPOPT.

It works on the Modelica text of an explicit ODE (for instance the `building_mpc` model that
[trano](https://github.com/andoludo/trano) generates with the FastSmoothBuildingsMPC library) and does not depend on trano.

```python
from trano_optimization import CasadiModel, OptimalControl

model = CasadiModel.from_modelica(source, "house.building_mpc")
result = OptimalControl(model).solve(initial_state, disturbances, comfort_lower, price)
```

A model that uses a Modelica library without holding it gives rumoca the folder of the library:

```python
import fastsmoothbuildings

model = CasadiModel.from_modelica(source, "house.building_mpc", roots=[fastsmoothbuildings.LIBRARY])
```

## Installation

```bash
pip install trano-optimization
```

This installs rumoca 0.10.2 from PyPI, which translates flat models. The models of the FastSmoothBuildings libraries are
made of connected components, which rumoca exports to CasADi from 0.10.3 only, not released yet: install it from
its main branch (Rust toolchain), as `[tool.uv.sources]` of `pyproject.toml` does.

```bash
pip install "rumoca @ git+https://github.com/CogniPilot/rumoca@33c21141791cbc341f4788ff6353d2f49d1c740a#subdirectory=crates/rumoca-bind-python"
```

## Development

```bash
uv sync         # builds rumoca from its git source (Rust toolchain)
make linting
make tests
```
