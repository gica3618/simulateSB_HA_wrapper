remember to do `source ~ahirota/setupEnvCXY.sh` before running this script

usage:

- with project code: `python simulateSB_HAs.py <project code> <SB name> -C <array config> -c <correlator> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step>`

- with xml: `python simulateSB_HAs.py <xml filename> -C <array config> -c <correlator> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step>`

default values:
- `min_HA`: -4
- `max_HA`: 3
- `HA_step`: 1

examples:
- Simulate all HAs between -4h and 3h: `python simulateSB_HAs.py 2023.1.00578.S HD_16329_a_09_TM1`
- Specify antenna configuration and HA range (from 1h to 2h in steps of 0.2h): `python simulateSB_HAs.py 2023.1.00578.S HD_16329_a_09_TM1 -C c43-1 --min_HA 1 --max_HA 2 --HA_step 0.2`
