# LoRa Network Simulator 3.0

This repository contains a lightweight LoRa network simulator written in Python. The implementation is based on the FLoRa model but greatly simplified so it can run without OMNeT++.

The latest version lives in the `VERSION_3` directory.

## Features

- Duty cycle enforcement to mimic real LoRa constraints
- Optional node mobility with Bezier interpolation
- Multi-channel radio support
- Advanced channel model with loss and noise parameters
- Initial spreading factor and power selection
- Basic LoRaWAN layer with LinkADRReq/LinkADRAns

## Quick start

```bash
# Clone the repository and install dependencies
cd VERSION_3
python3 -m venv env
source env/bin/activate  # On Windows use env\Scripts\activate
pip install -r requirements.txt

# Launch the dashboard
panel serve dashboard.py --show

# Or run a simulation via the CLI
python run.py --nodes 20 --steps 100
```

For a detailed description of all options, see `VERSION_3/README.md`.

This project is licensed under the [MIT License](LICENSE).
