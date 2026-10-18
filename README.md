# trano-optimization

Optimal control, moving horizon estimation and simulation of Modelica models: [rumoca](https://github.com/CogniPilot/rumoca)
translates the model into a CasADi function, solved by direct collocation with IPOPT.

It works on the Modelica text of an explicit ODE (for instance the `building_mpc` model that
[trano](https://github.com/andoludo/trano) generates with its FastModelMPC library) and does not depend on trano.

```python
from trano_optimization import CasadiModel, OptimalControl

model = CasadiModel.from_modelica(source, "house.building_mpc")
result = OptimalControl(model).solve(initial_state, disturbances, comfort_lower, price)
```

## Development

```bash
uv sync         # builds rumoca from its git source (Rust toolchain)
make linting
make tests
```
