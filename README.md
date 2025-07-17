remember to do `source ~ahirota/setupEnvCXY.sh` before running this script

usage:

- with project code and SB name:
  <br>`python simulate_HAs.py <project code> <SB name> -C <array config> -c <correlator> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step> --obs_date=<observation date> --writeQueryLog`

- with xml file:
  <br>`python simulate_HAs.py <xml filename> -C <array config> -c <correlator> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step> --obs_date=<observation date> --writeQueryLog`
  <br>Note that `<xml filename>` needs to end with .xml.

- with aot file to simulate all SBs of a project:
  <br>`python simulate_HAs.py <aot filename> -C <array config> -c <correlator> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step> --obs_date=<observation date> --writeQueryLog`
  <br>Note that `<aot filename>` needs to end with .aot. Note also that if you specify `<array config>`, that configuration will be used for all SBs.

default values:
- `min_HA`: -3 if DEC > -5 deg, otherwise -4 (same as DSA)
- `max_HA`: 2 if DEC > -5 deg, otherwise 3 (same as DSA)
- `HA_step`: 1
- `obs_date`: today

If the option `--writeQueryLog` is specified, calibrator queries and an overview of available calibrators are saved into text files.

examples:
- Simulate all HAs as considered by the DSA, with steps of 1h: `python simulate_HAs.py 2023.1.00578.S HD_16329_a_09_TM1`
- Specify antenna configuration and HA range (from 1h to 2h in steps of 0.2h): `python simulate_HAs.py 2023.1.00578.S HD_16329_a_09_TM1 -C c43-1 --min_HA 1 --max_HA 2 --HA_step 0.2`
- Specify a particular date of observation and save calibrator query information: `python simulate_HAs.py 2023.1.00578.S HD_16329_a_09_TM1 --obs_date=2024-11-08 --writeQueryLog`
- Simulate all SBs of a project and save calibrator query information: `python simulate_HAs.py 2023.1.00578.S.aot --writeQueryLog`
