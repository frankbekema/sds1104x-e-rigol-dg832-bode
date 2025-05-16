# sds1104x-e-rigol-dg832-bode
SDS1104X-E bode plot with Rigol DG832 function generator, based on https://uuki.kapsi.fi/sds1104bode.html

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
python <device id>
```
Retrieve devices:
```
python list_devices.py
```

Inspired by: https://uuki.kapsi.fi/sds1104bode.html