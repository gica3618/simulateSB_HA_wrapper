remember to do `source ~ahirota/setupEnvCXY.sh` before running this script

usage:

- with project code: `python simulateSB_HAs.py <project code> <SB name> -C <array config> -c <correlator> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step> --obs_date=<observation date>`

- with xml: `python simulateSB_HAs.py <xml filename> -C <array config> -c <correlator> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step> --obs_date=<observation date>`

default values:
- `min_HA`: -3 if DEC > -5 deg, otherwise -4 (same as DSA)
- `max_HA`: 2 if DEC > -5 deg, otherwise 3 (same as DSA)
- `HA_step`: 1
- `obs_date`: today

examples:
- Simulate all HAs as considered by the DSA, with steps of 1h: `python simulateSB_HAs.py 2023.1.00578.S HD_16329_a_09_TM1`
- Specify antenna configuration and HA range (from 1h to 2h in steps of 0.2h): `python simulateSB_HAs.py 2023.1.00578.S HD_16329_a_09_TM1 -C c43-1 --min_HA 1 --max_HA 2 --HA_step 0.2`
- Specify a particular date of observation: `python simulateSB_HAs.py 2023.1.00578.S HD_16329_a_09_TM1 --obs_date=2024-11-08`