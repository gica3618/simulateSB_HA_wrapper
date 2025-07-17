#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 16 10:05:21 2024

@author: gianni
"""

#usage of this script:

# using project code: 
# python simulateSB_HAs.py <project code> <SB name> -C <array config> -c <correlator>
# --min_HA <min HA> --max_HA <max HA> --HA_step <HA step> --obs_date <YYYY-MM-DD> --writeQueryLog

# using xml (note that the file needs to end in .xml)
# python simulateSB_HAs.py <xml filename> -C <array config> -c <correlator>
# --min_HA <min HA> --max_HA <max HA> --HA_step <HA step> --obs_date <YYYY-MM-DD> --writeQueryLog

#using aot to simulate all SBs of a project (file needs to end in .aot;
# also, you cannot specify the configuration)
# python simulateSB_HAs.py <aot filename> -c <correlator> --min_HA <min HA> 
# --max_HA <max HA> --HA_step <HA step> --obs_date <YYYY-MM-DD> --writeQueryLog


import argparse
import simulator

print('remember to do "source ~ahirota/setupEnvCXY.sh" before running this script')

parser = argparse.ArgumentParser()
parser.add_argument('sim_request',type=str)
#default takes care of the case where xml file is provided:
parser.add_argument('sb_name',type=str,default='',nargs='?')
for optional_argument,short in\
                    simulator.SBSimulation.simulateSB_optional_arguments.items():
    parser.add_argument(f"-{short}",dest=optional_argument)
parser.add_argument('--min_HA',type=float,default=None)
parser.add_argument('--max_HA',type=float,default=None)
parser.add_argument('--HA_step',type=float,default=1)
parser.add_argument('--obs_date',type=str,default=None)
parser.add_argument('--writeQueryLog',action='store_true')
args = parser.parse_args()

if args.min_HA is not None and args.max_HA is not None:
    assert args.min_HA < args.max_HA,'min_HA needs to be smaller than max_HA'
assert args.HA_step > 0,'HA step needs to be larger than 0'

sim = simulator.Simulation(args=args)
sim.run()