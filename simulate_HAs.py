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

print('remember to do "source ~ahirota/setupEnvCXY.sh" before running this script')

parser = argparse.ArgumentParser()
parser.add_argument("positional_args", nargs="+")
parser.add_argument('--min_HA',type=float,default=None)
parser.add_argument('--max_HA',type=float,default=None)
parser.add_argument('--HA_step',type=float,default=1)
parser.add_argument('--obs_date',type=str,default=None)
parser.add_argument('--writeQueryLog',action='store_true')
args = parser.parse_args()

sim = simulator.Simulation(args=args)
sim.run()