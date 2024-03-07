remember to do "source ~ahirota/setupEnvCXY.sh" before running this script

usage:

- with project code: `python simulateSB_HAs.py <project code> <SB name> -C <array config> -c <correlator> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step>`

- with xlm: `python simulateSB_HAs.py <xml filename> -C <array config> -c <correlator> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step>`

default values:
- min_HA: -4
- max_HA: 3
- HA_step: 1
