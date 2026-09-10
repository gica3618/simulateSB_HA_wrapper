# Usage

- with project code and SB name:
  <br>`simulate_HAs.py <project code> <SB name> <array config> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step> --obs_date=<observation date> --writeQueryLog`

- with xml file:
  <br>`simulate_HAs.py <xml filename> <array config> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step> --obs_date=<observation date> --writeQueryLog`
  <br>Note that `<xml filename>` needs to end with .xml.

- with aot file to simulate all SBs of a project:
  <br>`simulate_HAs.py <aot filename> <array config> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step> --obs_date=<observation date> --writeQueryLog`
  <br>Note that `<aot filename>` needs to end with .aot. Note also that `<array config>` will be used for all SBs.

For the array configuration, the following options are available:
- 'c43-1',...,'c43-10' (12m configurations)
- '7m'
- '7m_with_TP' (for 7m SBs that require TP antennas, typically high frequency)
- 'TP'
- 'default' (run simulateSB.py without specifying configuration)
- custom .cfg file provided by the user\

If the option `--writeQueryLog` is specified, calibrator queries and an overview of available calibrators are saved into text files.

default values:
- `min_HA`: -3 if DEC > -5 deg, otherwise -4 (same as DSA)
- `max_HA`: 2 if DEC > -5 deg, otherwise 3 (same as DSA)
- `HA_step`: 1
- `obs_date`: today

examples:
- Simulate all HAs as considered by the DSA, with steps of 1h:
  <br>`simulate_HAs.py 2023.1.00578.S HD_16329_a_09_TM1 c43-3`
- Specify HA range (from 1h to 2h in steps of 0.2h):
  <br>`simulate_HAs.py 2023.1.00578.S HD_16329_a_09_TM1 c43-1 --min_HA 1 --max_HA 2 --HA_step 0.2`
- Simulate high frequency 7m SB (xml) with additional TP antennas:
  <br>`simulate_HAs.py 2023.1.00452.S SM_22409_a_09_7M 7m_with_TP`
- Specify a particular date of observation and save calibrator query information:
  <br>`simulate_HAs.py 2023.1.00578.S HD_16329_a_09_TM1 c43-5 --obs_date=2024-11-08 --writeQueryLog`
- Simulate an xml file, and specify the antenna configuration by a cfg file:
  <br>`simulate_HAs.py HD_16329_a_09_TM1 my_antenna_config.cfg`
- Simulate all SBs of a project and save calibrator query information. Run simulateSB.py for each SB without specifying the configuration:
  <br>`simulate_HAs.py 2023.1.00578.S.aot default --writeQueryLog`
