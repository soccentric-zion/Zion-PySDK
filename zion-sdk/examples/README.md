# Examples

Each script is self-contained. Pass the Acadia client address as the only argument
(defaults to `127.0.0.1:50051`):

```bash
python examples/02_imu_oneshot.py 192.168.1.50:50051
```

To exercise the examples without real hardware, point them at the in-process
fake server used by the test suite:

```bash
python -c "
from tests.fakes.fake_server import FakeServer
srv = FakeServer(); print(srv.start())
input('press enter to stop...')
srv.stop()
"
```

## Numbered walk-throughs

| # | File | What it shows |
|---|------|---------------|
| 01 | `01_connect_and_discover.py` | Open a connection, list available peripherals. |
| 02 | `02_imu_oneshot.py` | Run a one-shot test and extract metric values via `zion_sdk.metric_value()`. |
| 03 | `03_imu_monitor_stream.py` | Stream IMU samples for a fixed duration. |
| 04 | `04_event_trigger.py` | Arm an event and wait for it to fire (two forms: `test_name` + freeform `expression`). |
| 05 | `05_long_running_test.py` | Start a background long-running session, poll for results, stop. |
| 06 | `06_self_test_all.py` | Run every peripheral's `self_test()` and print pass/fail. |
| 07 | `07_build_an_app.py` | A small real app: discover, run a one-shot per peripheral, emit a JSON report. |

## Per-peripheral notes

Every Acadia module supports the same five test modes (`oneshot`, `monitor`,
`event`, `long_running`, `self_test`) and the same lifecycle controls
(`pause`, `resume`, `stop`). The numbered examples above cover IMU and CPU
because they have the richest fake-server fixtures; swapping in a different
module is a one-line change:

```python
mod = dev.peripheral("ethernet")     # or "gpio", "can_bus", "i2c", ...
result = mod.run_oneshot()
```

See [docs/peripherals.md](../docs/peripherals.md) for the full module list,
their `Config` fields, and metric semantics.
