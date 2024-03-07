#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 16 10:05:21 2024

@author: gianni
"""

#usage of this script:
# using project code: 
# python simulateSB_allHA.py <project code> <SB name> -C <array config> -c <correlator> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step>
# using xlm:
# python simulateSB_allHA.py <xml filename> -C <array config> -c <correlator> --min_HA <min HA> --max_HA <max HA> --HA_step <HA step>

#for reference, usage of simulateSB.py:
# simulateSB.py <project code> <SB name> <EPOCH> -C <array config> -c <correlator>
# simulateSB.py <xml filename> <EPOCH> -C <array config> -c <correlator>

import argparse
import subprocess
import itertools
import shutil
import os
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('project_code_or_xml',type=str)
parser.add_argument('sb_name',type=str,default='',nargs='?') #default takes care of the case where xml file is provided
simulateSB_optional_arguments = {'array_config':'C','correlator':'c'}
for optional_argument,short in simulateSB_optional_arguments.items():
    parser.add_argument(f"-{short}",dest=optional_argument)
parser.add_argument('--min_HA',type=float,default=-4)
parser.add_argument('--max_HA',type=float,default=3)
parser.add_argument('--HA_step',type=float,default=1)
args = parser.parse_args()

assert args.min_HA < args.max_HA,'min_HA needs to be smaller than max_HA'
assert args.HA_step > 0,'HA step needs to be larger than 0'

HAs = [args.min_HA,]
HA_counter = 1
while True:
    new_HA = args.min_HA + HA_counter*args.HA_step
    if new_HA > args.max_HA:
        break
    HAs.append(new_HA)
    HA_counter += 1

def identify_error(pipes):
    pipe_messages = {key:p.split('\n') for key,p in pipes.items()}
    pipe_messages = {key:[m for m in messages if m!=''] for key,messages
                     in pipe_messages.items()}
    #check messages, starting from the latest
    msg_iterator = itertools.zip_longest(pipe_messages['stdout'][::-1],
                                         pipe_messages['stderr'][::-1],
                                         fillvalue='')
    max_messages_to_go_back = 5
    for i,(std_msg,error_msg) in enumerate(msg_iterator):
        #give preference to error_msg (i.e. check it first):
        for msg in (error_msg,std_msg):
            casefolded_msg = msg.casefold()
            if 'error' in casefolded_msg\
                                 or 'exception' in casefolded_msg:
                return msg
        if i >= max_messages_to_go_back-1:
            break
    print('did not find error message, will take last output'
          +' of stdout instead')
    return pipes['stdout'][-1]

def ask_yes_no_with_yes_as_default(question):
    print(question)
    answer = None
    while answer not in ('','y','n'):
        answer = input('([y]/n):')
    if answer == 'n':
        return False
    else:
        assert answer in ('','y')
        return True

print('remember to do "source ~ahirota/setupEnvCXY.sh" before running this script')

log_folder = f'log_files_{args.project_code_or_xml}'
if os.path.isdir(log_folder):
    remove_existing_log_folder = ask_yes_no_with_yes_as_default(
                                    f'remove existing log files in {log_folder}?')
    if remove_existing_log_folder:
        print(f'deleting folder {log_folder}')
        shutil.rmtree(log_folder)
    else:
        sys.exit('aborting, please remove or rename folder containing log files')
os.mkdir(log_folder)

results = []
for HA in HAs:
    epoch = f'TRANSIT{HA:+}h'
    command = f'simulateSB.py {args.project_code_or_xml} {args.sb_name} {epoch}'
    for optional_argument,short in simulateSB_optional_arguments.items():
        value = vars(args)[optional_argument]
        if value is not None:
            command += f' -{short} {value}'
    print(f'executing command: {command}')
    output = subprocess.run(command,shell=True,universal_newlines=True,
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if output.returncode != 0:
        pipes = {'stdout':output.stdout,'stderr':output.stderr}
        errormessage = identify_error(pipes=pipes)
        results.append(errormessage)
    else:
        results.append('success')
    if 'xml' in args.project_code_or_xml:
        log_files_base = f'log_{args.project_code_or_xml}'
    else:
        log_files_base = f'log_{args.project_code_or_xml}_{args.sb_name}.xml'
    log_files = [f'{log_files_base}_{ID}.txt' for ID in
                 ('OSS_summary','OSS','scan_list')]
    for log_file in log_files:
        if os.path.isfile(log_file):
            new_name = Path(log_file).stem + f'_HA{HA:+}h.txt'
            os.rename(src=log_file,dst=os.path.join(log_folder,new_name))

for HA,result in zip(HAs,results):
    print(f'{HA}h: {result}')

keep_log_files = ask_yes_no_with_yes_as_default('keep log files?')
if not keep_log_files:
    print('going to delete log files')
    shutil.rmtree(log_folder)
else:
    print(f'log files can be found in {log_folder}')