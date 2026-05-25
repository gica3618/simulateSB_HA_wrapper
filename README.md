# Usage

remember to do `source ~ahirota/setupEnvCXY.sh` before running this script (replace 'XY' by the cycle number, e.g. setupEnvC12.sh)

- with project code and SB name:
  <br>`python simulate_HAs.py <project code> <SB name> <array config> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step> --obs_date=<observation date> --writeQueryLog`

- with xml file:
  <br>`python simulate_HAs.py <xml filename> <array config> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step> --obs_date=<observation date> --writeQueryLog`
  <br>Note that `<xml filename>` needs to end with .xml.

- with aot file to simulate all SBs of a project:
  <br>`python simulate_HAs.py <aot filename> <array config> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step> --obs_date=<observation date> --writeQueryLog`
  <br>Note that `<aot filename>` needs to end with .aot. Note also that `<array config>` will be used for all SBs.

For the array configuration, the user can specify pre-defined configurations (e.g. 'TP', '7m', 'c43-1' to 'c43-10') or specify a configuration file (e.g. 'aca.cm10.pm3.cfg '). The user can also specify 'default'. In that case, simulateSB.py will decide which configuration it will simulate.

If the option `--writeQueryLog` is specified, calibrator queries and an overview of available calibrators are saved into text files.

default values:
- `min_HA`: -3 if DEC > -5 deg, otherwise -4 (same as DSA)
- `max_HA`: 2 if DEC > -5 deg, otherwise 3 (same as DSA)
- `HA_step`: 1
- `obs_date`: today

examples:
- Simulate all HAs as considered by the DSA, with steps of 1h: `python simulate_HAs.py 2023.1.00578.S HD_16329_a_09_TM1 c43-3`
- Specify antenna configuration and HA range (from 1h to 2h in steps of 0.2h): `python simulate_HAs.py 2023.1.00578.S HD_16329_a_09_TM1 c43-1 --min_HA 1 --max_HA 2 --HA_step 0.2`
- Specify a particular date of observation and save calibrator query information: `python simulate_HAs.py 2023.1.00578.S HD_16329_a_09_TM1 c43-5 --obs_date=2024-11-08 --writeQueryLog`
- Simulate all SBs of a project and save calibrator query information. Let simulateSB.py decide the array configuration for each SB: `python simulate_HAs.py 2023.1.00578.S.aot default --writeQueryLog`

# Make the script runnable from anywhere
If you want to be able to run the wrapper from anywhere (not just from the directory containing the two python files), proceed as follows:
1. Place the two python files (simulate_HAs.py and simulator.py) into a dedicated directory, for example simulateSB_HA_wrapper
2. Make simulate_HAs.py executable: `chmod +x simulate_HAs.py`
3. Add the directory containing the two python files to your PATH. To do this, add the following lines to your .bash_profile file (this file is found in your home directory on OSS):
    1. `PATH="$HOME/simulateSB_HA_wrapper:$PATH"` (assuming the directory simulateSB_HA_wrapper is in your home directory)
    2. `export PATH` (this line might already be there)

From next time you log into OSS, you will be able to run the wrapper from anywhere. Just be sure to replace `python simulate_HAs.py` by simply `simulate_HAs.py` (for example,  `simulate_HAs.py 2023.1.00578.S HD_16329_a_09_TM1 c43-3`)
