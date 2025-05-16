# sds1104x-e-rigol-dg832-bode
SDS1104X-E bode plot with Rigol DG832 function generator, based on https://uuki.kapsi.fi/sds1104bode.html

Install UltraSigma (Instrument Connectivity Driver) from https://www.rigolna.com/products/waveform-generators/dg800/?srsltid=AfmBOoosuh0qzyOOvC4efaW1lefd1NyxCCBAJEkq2YHabCMBlVTw6ZMq.

Create venv:
```
python -m venv env
```
Activate venv (Windows, in project root):
```
env\Scripts\activate
```
Install:
```
pip install -r requirements.txt
```
Run in dummy mode (no signal generator):
```
python bode.py
```
Run with signal generator
```
python bode.py <device id>
```
For my rigol device this is: USB0::0x1AB1::0x0643::DG8A220300107::INSTR

Retrieve devices:
```
python list_devices.py
```