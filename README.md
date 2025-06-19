# LoRa Network Simulator 3.0

This repository contains a lightweight LoRa network simulator implemented in Python. The latest code resides in the `VERSION_3` directory and is based on a simplified version of the FLoRa model so it can run without OMNeT++.

## Features
- Duty cycle enforcement to mimic real LoRa constraints
- Optional node mobility with Bezier interpolation
- Multi-channel radio support
- Advanced channel model with loss and noise parameters
- Initial spreading factor and power selection
- Basic LoRaWAN layer with LinkADRReq/LinkADRAns

## Quick start

```bash
# Install dependencies
cd VERSION_3
python3 -m venv env
source env/bin/activate  # On Windows use env\Scripts\activate
pip install -r requirements.txt

# Launch the dashboard
panel serve dashboard.py --show

# Run a simulation
python run.py --nodes 20 --steps 100
```

You can also execute the simulator directly from the repository root:

```bash
python VERSION_3/run.py --nodes 20 --steps 100
```

For a detailed description of all options, see `VERSION_3/README.md`.
