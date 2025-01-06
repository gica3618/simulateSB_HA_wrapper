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
# using xlm:
# python simulateSB_HAs.py <xml filename> -C <array config> -c <correlator>
# --min_HA <min HA> --max_HA <max HA> --HA_step <HA step> --obs_date <YYYY-MM-DD> --writeQueryLog

#for reference, usage of simulateSB.py:
# simulateSB.py <project code> <SB name> <EPOCH> -C <array config> -c <correlator>
# simulateSB.py <xml filename> <EPOCH> -C <array config> -c <correlator>

import argparse
import subprocess
import itertools
import shutil
import os
import sys
import xml_reader
import glob

print('remember to do "source ~ahirota/setupEnvCXY.sh" before running this script')

parser = argparse.ArgumentParser()
parser.add_argument('project_code_or_xml',type=str)
parser.add_argument('sb_name',type=str,default='',nargs='?') #default takes care of the case where xml file is provided
simulateSB_optional_arguments = {'array_config':'C','correlator':'c'}
for optional_argument,short in simulateSB_optional_arguments.items():
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

xml_was_provided = 'xml' in args.project_code_or_xml
if xml_was_provided:
    xml_file = xml_reader.OT_XML_File(args.project_code_or_xml)
else:
    xml_file = xml_reader.OT_XML_File.from_download(
                            project_code=args.project_code_or_xml,SB=args.sb_name)

rep_coord = xml_file.get_representative_coordinates()
#DSA will consider the following HA limits:
if rep_coord.dec.deg >= -5:
    DSA_min_HA = -3
    DSA_max_HA = 2
else:
    DSA_min_HA = -4
    DSA_max_HA = 3

if args.min_HA is None:
    print(f'no min HA provided, thus adopting the min HA considered by DSA: {DSA_min_HA}h')
    min_HA = DSA_min_HA
else:
    print(f'using user-provided min HA of {args.min_HA}h')
    min_HA = args.min_HA
if args.max_HA is None:
    print(f'no max HA provided, thus adopting the max HA considered by DSA: {DSA_max_HA}h')
    max_HA = DSA_max_HA
else:
    print(f'using user-provided max HA of {args.max_HA}h')
    max_HA = args.max_HA
print(f'HA step: {args.HA_step}h')

HAs = [min_HA,]
HA_counter = 1
while True:
    new_HA = min_HA + HA_counter*args.HA_step
    if new_HA > max_HA:
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

log_folder = f'log_files_{args.project_code_or_xml}'
if args.sb_name != '':
    log_folder += f'_{args.sb_name}'
if os.path.isdir(log_folder):
    remove_existing_log_folder = ask_yes_no_with_yes_as_default(
                                    f'remove existing log files in folder {log_folder}?')
    if remove_existing_log_folder:
        print(f'deleting folder {log_folder}')
        shutil.rmtree(log_folder)
    else:
        sys.exit('aborting, please remove or rename folder containing log files')
os.mkdir(log_folder)

if xml_was_provided:
    log_files_base = f'log_{args.project_code_or_xml}'
else:
    log_files_base = f'log_{args.project_code_or_xml}_{args.sb_name}.xml'
def get_log_files():
    return glob.glob(f'{log_files_base}_*.txt')
old_log_files = get_log_files()
if len(old_log_files) > 0:
    print('log files from previous run(s):')
    for lf in old_log_files:
        print(lf)
    remove_log_files = ask_yes_no_with_yes_as_default('remove these log files?')
    if remove_log_files:
        for lf in old_log_files:
            print(f'deleting {lf}')
            os.remove(lf)
    else:
        sys.exit('aborting, please remove log files')

results = []
for HA in HAs:
    epoch = f'TRANSIT{HA:+}h'
    if args.obs_date is not None:
        epoch += f',{args.obs_date}'
    command = f'simulateSB.py {args.project_code_or_xml} {args.sb_name} {epoch}'
    for optional_argument,short in simulateSB_optional_arguments.items():
        value = vars(args)[optional_argument]
        if value is not None:
            command += f' -{short} {value}'
    if args.writeQueryLog:
        command += ' --writeQueryLog'
    print(f'executing command: {command}')
    output = subprocess.run(command,shell=True,universal_newlines=True,
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if output.returncode != 0:
        pipes = {'stdout':output.stdout,'stderr':output.stderr}
        errormessage = identify_error(pipes=pipes)
        results.append(errormessage)
    else:
        results.append('success')
    log_files = get_log_files()
    HA_log_folder = os.path.join(log_folder,f'HA{HA:+}h')
    os.mkdir(HA_log_folder)
    for log_file in log_files:
        shutil.move(src=log_file,dst=HA_log_folder)

for HA,result in zip(HAs,results):
    print(f'{HA}h: {result}')

if not xml_was_provided:
    print('deleting downloaded xml')
    xml_filename = f'{args.project_code_or_xml}_{args.sb_name}.xml'
    os.remove(xml_filename)
sim_result_filename = 'SimulatedCalResultsData.dat'
print(f'deleting {sim_result_filename}')
os.remove(sim_result_filename)

keep_log_files = ask_yes_no_with_yes_as_default('keep log files?')
if not keep_log_files:
    shutil.rmtree(log_folder)
    print('log files deleted')
else:
    print(f'log files can be found in {log_folder}')