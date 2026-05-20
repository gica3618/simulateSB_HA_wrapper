#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 15 14:41:43 2025

@author: gianni
"""

import itertools
import os
import shutil
import sys
import glob
import subprocess
import xml.etree.ElementTree as ET
from astropy.coordinates import SkyCoord
from astropy import units as u
from pathlib import Path


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

def ask_question_exit_if_answer_no(question):
    proceed = ask_yes_no_with_yes_as_default(question)
    if not proceed:
        sys.exit("exiting")


class OT_XML_File():
    namespaces = {'sbl':'Alma/ObsPrep/SchedBlock',
                  'prj':"Alma/ObsPrep/ObsProject",
                  'val':"Alma/ValueTypes"}
    long_lat_keys = {'longitude':'ra','latitude':'dec'}

    def __init__(self,filepath,xml_str=None):
        if filepath is not None:
            assert xml_str is None
            tree = ET.parse(filepath)
            self.root = tree.getroot()
        else:
            self.root = ET.fromstring(xml_str)

    @staticmethod
    def download_xml_str(project_code,SB):
        #I took this code directly from simulateSB.py and simplified it
        scriptGetSB = "/groups/science/scripts/P2G/getsb/getsb.py"
        if not os.path.isfile(scriptGetSB):
            scriptGetSB = "/users/ahirota/AIV/science/scripts/P2G/getsb/getsb.py"
        try:
            import cx_Oracle
            serverName = None
        except:
            print("cx_Oracle is not available, and thus will run getsb.py"+
                  " on red-osf")
            serverName = "red-osf.osf.alma.cl"
        if serverName:
            userName = os.getenv("USER")
            cmd = ["ssh"]
            cmd.append(f"{userName}@{serverName}")
            scriptName = "PYTHONPATH=/users/ahirota/local/lib64/python2.6/"\
                          +"site-packages/cx_Oracle-5.2.1-py2.6-linux-x86_64.egg"\
                          +f":$PYTHONPATH {scriptGetSB}"
            cmd.append(f"{scriptName} -p '{project_code}' -s '{SB}'")
            cmd.append("-S ora.sco.alma.cl:1521/ONLINE.SCO.CL")
        else:
            cmd = [scriptGetSB]
            cmd.extend(["-p", project_code, "-s", SB])
            cmd.extend(["-S", "ora.sco.alma.cl:1521/ONLINE.SCO.CL"])
        print("# Retrieving SB xml with the following command [%s]"\
                      % (" ".join(cmd)))
        p = subprocess.Popen(cmd,stdout=subprocess.PIPE,env=None)
        xml_str, _ = p.communicate()
        if hasattr(sys.stdout,"detach"):
            # Py3
            xml_str = xml_str.decode("utf-8")
        return xml_str

    @staticmethod
    def download_xml_file(project_code,SB,filename=None):
        xml_str = OT_XML_File.download_xml_str(project_code=project_code,SB=SB)
        if filename is None:
            filename = f'{SB}.xml'
        if os.path.exists(filename):
            raise RuntimeError(f'error downloading {filename}, already'
                               +' exists; please delete')
        with open(filename,"w") as file:
            file.write(xml_str)
        return filename

    @classmethod
    def from_download(cls,project_code,SB):
        xml_str = cls.download_xml_str(project_code=project_code,SB=SB)
        return cls(filepath=None,xml_str=xml_str)

    def find_unique_element(self,tag):
        elements = self.root.findall(tag,namespaces=self.namespaces)
        n_elements = len(elements)
        assert n_elements == 1, f'found {n_elements} matching elements for {tag}'
        return elements[0]

    def read_coordinates(self,coord_data):
        coord = {}
        for xml_key,output_key in self.long_lat_keys.items():
            element = coord_data.find(f'val:{xml_key}',namespaces=self.namespaces)
            assert element.attrib['unit'] == 'deg'
            coord[output_key] = float(element.text)
        return SkyCoord(ra=coord['ra']*u.deg,dec=coord['dec']*u.deg)

    def get_representative_coordinates(self):
        tag = 'sbl:SchedulingConstraints/sbl:representativeCoordinates'
        coord_data = self.find_unique_element(tag)
        return self.read_coordinates(coord_data=coord_data)

    def get_SB_name(self):
        return self.find_unique_element('prj:name').text

    def read_modeName(self):
        return self.find_unique_element('sbl:modeName').text

    def get_nominal_configurations(self):
         configs = self.root.findall('sbl:SchedulingConstraints/sbl:nominalConfiguration',
                                     namespaces=self.namespaces)
         return [c.text for c in configs]

    def read_RequiresTPAntennas(self):
        text = self.root.findtext('sbl:SchedulingConstraints/sbl:sbRequiresTPAntennas',
                                  namespaces=self.namespaces)
        if text is None: #not found
            return None
        if text == 'true':
            return True
        elif text == 'false':
            return False
        else:
            raise RuntimeError(f'unknown xml content for sbRequiresTPAntennas: {text}')


class SBSimulation():

    #simulateSB_optional_arguments = {'array_config':'C','correlator':'c'}
    #the following list is in the order of how queries are conducted by OSS!
    calibrator_query_identifiers = ['diffgain','bandpass','phase','check']

    def __init__(self,xml_file,log_folder,min_HA,max_HA,HA_step,obs_date,writeQueryLog,
                 array_config,check_array_config=True):
        self.xml_file = xml_file
        self.xml_data = OT_XML_File(filepath=xml_file)
        self.log_files_prefix = f'log_{xml_file}'
        self.log_folder = log_folder
        self.min_HA = min_HA
        self.max_HA = max_HA
        self.HA_step = HA_step
        self.obs_date = obs_date
        self.writeQueryLog = writeQueryLog
        self.array_config = array_config
        #self.correlator = correlator
        if check_array_config:
            self.check_array_config()

    def check_array_config(self):
        nominal_configs = self.xml_data.get_nominal_configurations()
        if "7M" in nominal_configs:
            self.check_7M_config()
            return
        if "TP" in nominal_configs:
            self.check_TP_config()
            return
        self.check_12M_config(nominal_configs=nominal_configs)

    def check_7M_config(self):
        requires_TP = self.xml_data.read_RequiresTPAntennas()
        if requires_TP and self.array_config in ("default","7M"):
            ask_question_exit_if_answer_no(
                           "WARNING: this 7M SB requires TP antennas, but requested "
                           +f"configuration '{self.array_config}' does not include TP antennas. Proceed?")
        if (not requires_TP) and "pm" in self.array_config:
            ask_question_exit_if_answer_no(
                   "WARNING: this 7M SB does not require TP antennas, but it looks like "
                   +f"your requested configuration '{self.array_config}' might include TP. Proceed?")

    def check_TP_config(self):
        if self.array_config not in ("default", "TP"):
            ask_question_exit_if_answer_no(
                 f"Do you really wish to simulate this TP SB with array configuration '{self.array_config}?'")

    def check_12M_config(self,nominal_configs):
        if (self.array_config.capitalize() not in nominal_configs
            and self.array_config != "default"):
            ask_question_exit_if_answer_no(
                f"Nominal configuration(s) of this SB: {nominal_configs}. Do "
                f"you really wish to simulate with configuration '{self.array_config}'?")

    def run(self):
        self.determine_HAs_to_simulate()
        self.remove_existing_log_files()
        self.run_simulations()
        if self.writeQueryLog:
            self.summarize_available_calibrators()
        self.print_results()

    def determine_HAs_to_simulate(self):
        rep_coord = self.xml_data.get_representative_coordinates()
        #DSA will consider the following HA limits:
        if rep_coord.dec.deg >= -5:
            DSA_min_HA = -3
            DSA_max_HA = 2
        else:
            DSA_min_HA = -4
            DSA_max_HA = 3
        if self.min_HA is None:
            print('no min HA provided, thus adopting the min HA considered by '
                  +f'DSA: {DSA_min_HA}h')
            min_HA = DSA_min_HA
        else:
            print(f'using user-provided min HA of {self.min_HA}h')
            min_HA = self.min_HA
        if self.max_HA is None:
            print('no max HA provided, thus adopting the max HA considered by'
                  f' DSA: {DSA_max_HA}h')
            max_HA = DSA_max_HA
        else:
            print(f'using user-provided max HA of {self.max_HA}h')
            max_HA = self.max_HA
        print(f'HA step: {self.HA_step}h')
        self.HAs = [min_HA,]
        HA_counter = 1
        while True:
            new_HA = min_HA + HA_counter*self.HA_step
            if new_HA > max_HA:
                break
            self.HAs.append(new_HA)
            HA_counter += 1

    @staticmethod
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

    def get_log_files(self):
        return glob.glob(f'{self.log_files_prefix}_*.txt')

    def remove_existing_log_files(self):
        old_log_files = self.get_log_files()
        if len(old_log_files) > 0:
            print('found existing log files (from previous run?):')
            for lf in old_log_files:
                print(lf)
            remove_log_files = ask_yes_no_with_yes_as_default(
                                                      'remove these log files?')
            if remove_log_files:
                for lf in old_log_files:
                    print(f'deleting {lf}')
                    os.remove(lf)
            else:
                sys.exit('aborting, please remove log files')

    def get_cal_query_file_names(self):
         return [f'{self.log_files_prefix}_{cal}_1.txt' for cal in
                 self.calibrator_query_identifiers]

    def determine_available_calibrators(self):
        available_calibrators = {}
        cal_query_filenames = self.get_cal_query_file_names()
        for cal_type,filename in zip(self.calibrator_query_identifiers,
                                     cal_query_filenames):
            if not os.path.isfile(filename):
                continue
            available_calibrators[cal_type] = []
            with open(filename,"r") as file:
                for line in file:
                    splitted = line.replace(' ','').split('|')
                    if len(splitted) > 2:
                        calibrator,reason = splitted[1],splitted[-2]
                        if calibrator == '':
                            continue
                        if calibrator[0] != '[':
                            #line is not containing a calibrator
                            continue
                        if reason != '':
                            #calibrator was rejected
                            continue
                        calibrator = calibrator.split(']')[0]
                        calibrator = calibrator.replace('[','')
                        available_calibrators[cal_type].append(calibrator)
        return available_calibrators

    def concatenate_cal_queries(self):
        output_filename = f'{self.log_files_prefix}_calibrator_queries.txt'
        cal_query_filenames = self.get_cal_query_file_names()
        with open(output_filename,'w') as outfile:
            for fname in cal_query_filenames:
                if os.path.isfile(fname):
                    with open(fname,'r') as infile:
                        outfile.write(infile.read())
                        outfile.write('\n\n######################################\n\n')
                    os.remove(fname)

    def move_log_files(self,HA):
        log_files = self.get_log_files()
        for log_f in log_files:
            shutil.move(src=log_f,dst=os.path.join(self.log_folder,f'HA{HA}h_{log_f}'))

    def run_simulations(self):
        self.results = []
        if self.writeQueryLog:
            self.available_calibrators = []
        for HA in self.HAs:
            epoch = f'TRANSIT{HA:+}h'
            if self.obs_date is not None:
                epoch += f',{self.obs_date}'
            command = f'simulateSB.py {self.xml_file} {epoch}'
            if self.array_config != "default":
                command += f' -C {self.array_config}'
            # for optional_argument,short in self.simulateSB_optional_arguments.items():
            #     value = getattr(self,optional_argument)
            #     if value is not None:
            #         command += f' -{short} {value}'
            if self.writeQueryLog:
                command += ' --writeQueryLog'
            print(f'executing command: {command}')
            output = subprocess.run(command,shell=True,universal_newlines=True,
                                    stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            if output.returncode != 0:
                pipes = {'stdout':output.stdout,'stderr':output.stderr}
                errormessage = self.identify_error(pipes=pipes)
                self.results.append(errormessage)
            else:
                self.results.append('success')
            if self.writeQueryLog:
                self.available_calibrators.append(
                                        self.determine_available_calibrators())
                self.concatenate_cal_queries()
            self.move_log_files(HA=HA)        

    def queried_calibrator_types(self):
        calibrator_types = []
        for available_cals in self.available_calibrators:
            calibrator_types += list(available_cals.keys())
        return list(set(calibrator_types))

    def summarize_available_calibrators(self):
        out_filename = os.path.join(self.log_folder,'available_calibrators.csv')
        calibrator_types = self.queried_calibrator_types()
        #order the calibrator types according to the query order:
        calibrator_types = sorted(
                             calibrator_types,
                             key=lambda x:self.calibrator_query_identifiers.index(x))
        with open(out_filename,'w') as file:
            file.write('HA,')
            file.write(','.join(calibrator_types))
            file.write('\n')
            for HA,available_cals in zip(self.HAs,self.available_calibrators):
                file.write(f'{HA},')
                for cal_type in calibrator_types:
                    if cal_type in available_cals:
                        #this calibrator type was queried for this hour angle
                        calibrators = available_cals[cal_type]
                        if len(calibrators) == 0:
                            file.write('None')
                        else:
                            file.write(';'.join(calibrators))
                    else:
                        #this calibrator type was not queried for this hour angle
                        file.write('not queried')
                    file.write(',')
                file.write('\n')

    def print_results(self):
        for HA,result in zip(self.HAs,self.results):
            print(f'{HA}h: {result}')

    def append_results_to_file(self,filename):
        with open(filename,'a') as file:
            for HA,result in zip(self.HAs,self.results):
                file.write(f'{HA}h: {result}\n')


class Simulation():

    sim_result_filename = 'SimulatedCalResultsData.dat'

    def __init__(self, args):
        self.args = args
        positional = args.positional_args
        if len(positional) == 2:
            self.handle_file_input(*positional)
        elif len(positional) == 3:
            self.handle_code_sb_input(*positional)
        else:
            raise ValueError("invalid number of positional arguments")
        self.check_HA_args()
        self.check_array_config()

    def handle_file_input(self, filename, array_config):
        self.array_config = array_config
        suffix = Path(filename).suffix
        if suffix == ".xml":
            self.input_mode = "xml"
            self.xml_files = [filename]
        elif suffix == ".aot":
            self.confirm_aot_usage()
            self.input_mode = "aot"
            self.xml_files = self.extract_xml_files_from_aot(filename)
        else:
            raise ValueError("invalid arguments")

    def handle_code_sb_input(self, project_code, sb_name, array_config):
        self.array_config = array_config
        self.input_mode = "sb"
        xml_filename = self.get_xml_filename(SB_name=sb_name)
        xml_file = OT_XML_File.download_xml_file(
            project_code=project_code,
            SB=sb_name,
            filename=xml_filename,
        )
        print(f"downloaded {xml_file}")
        self.xml_files = [xml_file]

    def confirm_aot_usage(self):
        ask_question_exit_if_answer_no(
            "ATTENTION: will use antenna configuration "
            f'"{self.array_config}" for all SBs. '
            "Do you want to proceed?"
        )

    def check_HA_args(self):
        if self.args.min_HA is not None and self.args.max_HA is not None:
            if self.args.min_HA >= self.args.max_HA:
                raise ValueError('min_HA needs to be smaller than max_HA')
        if self.args.HA_step <= 0:
            raise ValueError('HA step needs to be larger than 0')

    def check_array_config(self):
        if self.array_config == "default":
            print("user requests that simulateSB.py decides the array configuration to simulate")

    # def array_config_for_simulation(self):
    #     if self.array_config == "default":
    #         print("user requests that simulateSB.py decides the array configuration to simulate")
    #         return None
    #     else:
    #         return self.array_config

    # def __init__(self,args):
    #     self.args = args
    #     self.xml_was_provided = False
    #     self.aot_was_provided = False
    #     if len(args.positional_args) == 2:
    #         #case where xml or aot is provided (plus array config)
    #         filename,self.array_config = args.positional_args
    #         suffix = Path(filename).suffix
    #         if suffix == ".xml":
    #             self.xml_was_provided = True
    #             self.xml_files = [filename,]
    #             xml_filename, array_config = args
    #         elif suffix == ".aot":
    #             self.aot_was_provided = True
    #             proceed = ask_yes_no_with_yes_as_default(
    #                           'ATTENTION: will use antenna configuration'
    #                           +f' {self.array_config} for all SBs. Do you'
    #                           +' want to proceed?')
    #             if not proceed:
    #                 sys.exit('aborting')
    #             self.xml_files = self.extract_xml_files_from_aot(filename)
    #         else:
    #             raise ValueError("only xml or aot files can be used")
    #     elif len(args.positional_args) == 3:
    #         #case where project code, SB name and array config are provided
    #         project_code, sb_name, self.array_config = args.positional_args
    #         xml_filename = self.get_xml_filename(SB_name=sb_name)
    #         xml_file = OT_XML_File.download_xml_file(
    #                           project_code=project_code,SB=sb_name,
    #                           filename=xml_filename)
    #         print(f'downloaded {xml_file}')
    #         self.xml_files = [xml_file,]
    #     else:
    #         raise ValueError("invalid number of positional arguments")

    def aot_was_provided(self):
        return self.input_mode == "aot"

    def xml_was_provided(self):
        return self.input_mode == "xml"

    def run(self):
        #self.prepare_xml_files()
        self.prepare_log_folders()
        if self.aot_was_provided():
            self.prepare_summary_file()
        self.run_simulations()
        self.clean_up()

    @staticmethod
    def get_xml_filename(SB_name):
        return f'{SB_name}.xml'

    @staticmethod
    def extract_xml_files_from_aot(aot_file):
        print(f'going to extract xml files from {aot_file}')
        xml_pattern = 'Sch*.xml'
        old_xml_files = glob.glob(xml_pattern)
        if len(old_xml_files) > 0:
            raise RuntimeError('cannot extract xmls from .aot because some xmls'
                               +' already exist, please delete')
        os.system(f'unzip {aot_file} {xml_pattern}')
        extracted_xml_files = glob.glob(xml_pattern)
        output_xml_filenames = []
        for xml_file in extracted_xml_files:
            xml = OT_XML_File(xml_file)
            SB_name = xml.get_SB_name()
            new_xml_filename = Simulation.get_xml_filename(SB_name=SB_name)
            os.rename(xml_file,new_xml_filename)
            output_xml_filenames.append(new_xml_filename)
        print(f'extracted following xml files: {output_xml_filenames}')
        return output_xml_filenames

    # def prepare_xml_files(self):
    #     if self.xml_was_provided:
    #         self.xml_files = [self.args.sim_request,]
    #     elif self.aot_was_provided:
    #         if self.args.array_config is not None:
    #             proceed = ask_yes_no_with_yes_as_default(
    #                           'ATTENTION: will use antenna configuration'
    #                           +f' {self.args.array_config} for all SBs. Do you'
    #                           +' want to proceed?')
    #             if not proceed:
    #                 sys.exit('aborting')
    #         self.xml_files = self.extract_xml_files_from_aot(
    #                                      self.args.sim_request)
    #     else:
    #         SB_name = self.args.sb_name
    #         xml_file = OT_XML_File.download_xml_file(
    #                           project_code=self.args.sim_request,
    #                           SB=SB_name,filename=self.get_xml_filename(SB_name=SB_name))
    #         print(f'downloaded {xml_file}')
    #         self.xml_files = [xml_file,]

    def prepare_log_folders(self):
        self.log_folders = [f'log_files_{xml_file[:-4]}' for xml_file in self.xml_files]
        for log_folder in self.log_folders:
            if os.path.isdir(log_folder):
                remove_existing_log_folder = ask_yes_no_with_yes_as_default(
                            f'remove existing log folder {log_folder}?')
                if remove_existing_log_folder:
                    print(f'deleting folder {log_folder}')
                    shutil.rmtree(log_folder)
                else:
                    sys.exit('aborting, please remove or rename folder containing log files')
            os.mkdir(log_folder)

    def prepare_summary_file(self):
        self.summary_filename = f'{self.args.positional_args[0]}_simulation_summary.txt'
        if os.path.exists(self.summary_filename):
            print(f'deleting {self.summary_filename}')
            os.remove(self.summary_filename)

    def run_simulations(self):
        for xml_file,log_folder in zip(self.xml_files,self.log_folders):
            print(f'going to run simulations of {xml_file}')
            if self.aot_was_provided():
                with open(self.summary_filename,'a') as file:
                    file.write(f'\n{xml_file}\n')
            #If aot file was provided, I just ask about the array config at the start,
            #and not for each SB again:
            check_array_config = not self.aot_was_provided()
            sim = SBSimulation(
                        xml_file=xml_file,log_folder=log_folder,min_HA=self.args.min_HA,
                        max_HA=self.args.max_HA,HA_step=self.args.HA_step,
                        obs_date=self.args.obs_date,writeQueryLog=self.args.writeQueryLog,
                        array_config=self.array_config,check_array_config=check_array_config)
            sim.run()
            if self.aot_was_provided():
                sim.append_results_to_file(filename=self.summary_filename)
            print('\n------------------------------------------\n')

    def clean_up(self):
        if not self.xml_was_provided():
            for xml_file in self.xml_files:
                os.remove(xml_file)
                print(f'deleted {xml_file}')
        os.remove(self.sim_result_filename)
        print(f'deleted {self.sim_result_filename}')    
        keep_log_files = ask_yes_no_with_yes_as_default('keep log files?')
        if not keep_log_files:
            for log_folder in self.log_folders:
                shutil.rmtree(log_folder)
                print(f'deleted {log_folder}')
            if self.aot_was_provided():
                os.remove(self.summary_filename)
        else:
            print('log files can be found in following folder(s)): '
                  +f'{", ".join(self.log_folders)}')
            if self.aot_was_provided():
                print(f'summary file: {self.summary_filename}')


if __name__ == '__main__':
    xml = OT_XML_File('G022.25_a_09_7M_query.xml')