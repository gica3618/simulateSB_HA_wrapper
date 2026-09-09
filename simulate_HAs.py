#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 16 10:05:21 2024

@author: gianni
"""

#usage of this script:

# using project code: 
# python simulateSB_HAs.py <project code> <SB name> <array config>
# --min_HA <min HA> --max_HA <max HA> --HA_step <HA step> --obs_date <YYYY-MM-DD> --writeQueryLog

# using xml (note that the file needs to end in .xml)
# python simulateSB_HAs.py <xml filename> <array config>
# --min_HA <min HA> --max_HA <max HA> --HA_step <HA step> --obs_date <YYYY-MM-DD> --writeQueryLog

#using aot to simulate all SBs of a project (file needs to end in .aot)
# python simulateSB_HAs.py <aot filename> <array_config> --min_HA <min HA> 
# --max_HA <max HA> --HA_step <HA step> --obs_date <YYYY-MM-DD> --writeQueryLog


import argparse
import simulator


epilog = ("Examples:\n"
         +"1) Simulate all HAs as considered by the DSA, with steps of 1h:\n"
         +"simulate_HAs.py 2023.1.00578.S HD_16329_a_09_TM1 c43-3\n\n"
         +"2) Specify HA range (from 1h to 2h in steps of 0.2h):\n"
         +"simulate_HAs.py 2023.1.00578.S HD_16329_a_09_TM1 c43-1 --min_HA 1 "
         +"--max_HA 2 --HA_step 0.2\n\n"
         +"3) Specify a particular date of observation and save calibrator "
         +"query information:\n"
        +"simulate_HAs.py 2023.1.00578.S HD_16329_a_09_TM1 c43-5"
        +" --obs_date=2024-11-08 --writeQueryLog\n\n"
        +"4) Simulate a 7M SB using an xml file, and with a configuration file"
        +" that contains PM antennas, with steps of 0.25H:\n"
        +"simulate_HAs.py HD_16329_a_09_7M.xml aca.cm10.pm3.cfg --HA_step=0.25\n\n"
        +"5) Simulate all SBs of a project and save calibrator query information. Let "
        +"simulateSB.py decide the array configuration for each SB:\nsimulate_HAs.py "
        +"2023.1.00578.S.aot default --writeQueryLog")

parser = argparse.ArgumentParser(description="There are three ways of using this "
                                 +"wrapper:\n1) provide the project code and SB name"
                                 +"\n2) provide xml file\n3) provide"
                                 +" aot file. In this case, all SBs "
                                 +"contained in the aot file will be simulated.",
                                 epilog=epilog,
                                 formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("positional_args", nargs="+",
                    help="There are three options:\n1) <project code> <SB name> "
                         +"<array config>\n2) <xml filename> <array config>"
                         +"\n3) <aot filename> <array_config>\nFor the array configuration,"
                         +" the user can specify pre-defined configurations (e.g. 'TP',"
                         +" '7m', 'c43-1' to 'c43-10') or specify a configuration"
                         +" file (e.g. 'aca.cm10.pm3.cfg'). The user can also "
                         +"specify 'default'. In that case, simulateSB.py will "
                         +"decide which configuration it will simulate. Note that when "
                         +"simulating an aot file, all SBs will be simulated with the"
                         " same configuration.")
parser.add_argument('--min_HA',type=float,default=None,
                    help="Smallest HA to simulate. Default is the smallest HA considered"
                        +" by the DSA.")
parser.add_argument('--max_HA',type=float,default=None,
                    help="Largest HA to simulate. Default is the largest HA considered"
                        +" by the DSA.")
parser.add_argument('--HA_step',type=float,default=1, help="HA step size. Default is 1H.")
parser.add_argument('--obs_date',type=str,default=None,
                    help="Observation date to simulate in the format <YYYY-MM-DD>."
                        +"Default is today.")
parser.add_argument('--writeQueryLog',action='store_true',
                    help="Write query logs into separate files.")
args = parser.parse_args()

sim = simulator.Simulator(args=args)
sim.run()