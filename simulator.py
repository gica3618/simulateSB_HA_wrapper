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
import subprocess
import xml.etree.ElementTree as ET
from astropy.coordinates import SkyCoord
from astropy import units as u
from pathlib import Path
import tempfile
from concurrent.futures import ThreadPoolExecutor


#the following list is in the order of how queries are conducted by OSS!
calibrator_query_identifiers = ['diffgain','bandpass','phase','check']


def ask(question):
    print(question)
    answer = None
    while answer not in ('','y','n'):
        answer = input('([y]/n):')
    if answer == 'n':
        return False
    else:
        if answer not in ('','y'):
            raise RuntimeError("unexpected answer")
        return True

def ask_and_raise_error(question):
    proceed = ask(question)
    if not proceed:
        raise RuntimeError("aborted")

def xml_filename(SB):
    return f'{SB}.xml'


class WorkFolder:

    def __enter__(self):
        self.path = Path(tempfile.mkdtemp(prefix="sb_sim_"))
        return self.path

    def __exit__(self, exc_type, exc, tb):
        shutil.rmtree(self.path)


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
    def download_xml_file(project_code,SB,filepath=None):
        xml_str = OT_XML_File.download_xml_str(project_code=project_code,SB=SB)
        if filepath is None:
            filepath = Path(xml_filename(SB=SB))
        if filepath.is_file():
            raise RuntimeError(f'error downloading {filepath}, already'
                               +' exists; please delete')
        with open(filepath,"w") as file:
            file.write(xml_str)
        return filepath

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


class SingleHASimulation:

    def __init__(self,HA,xml_path,array_config,obs_date,writeQueryLog,log_folder):
        self.HA = HA
        self.xml_path = xml_path
        self.array_config = array_config
        self.obs_date = obs_date
        self.writeQueryLog = writeQueryLog
        self.log_folder = log_folder
        self.log_files_prefix = f'log_{xml_path.name}'

    def run(self):
        command = self.build_command()
        self.print_pseudo_command(command=command)
        with WorkFolder() as work_folder:
            process = subprocess.run(command,text=True,capture_output=True,cwd=work_folder)
            if process.returncode != 0:
                pipes = {'stdout':process.stdout,'stderr':process.stderr}
                result = self.identify_error(pipes=pipes)
            else:
                result = 'success'
            if self.writeQueryLog:
                available_cals = self.determine_available_calibrators(
                                                            work_folder=work_folder)
                self.concatenate_cal_queries(work_folder=work_folder)
            else:
                available_cals = None
            self.move_log_files(work_folder=work_folder)
        return result,available_cals

    def build_command(self):
        epoch = f'TRANSIT{self.HA:+}h'
        if self.obs_date is not None:
            epoch += f',{self.obs_date}'
        command = ["simulateSB.py", str(self.xml_path.absolute()), epoch]
        if self.array_config != "default":
            command.append("-C")
            if self.array_config.endswith(".cfg"):
                #array config file is used
                command.append( str(Path(self.array_config).absolute()) )
            else:
                #standard configuration is used, such as "7M" or "c43-3"
                command.append(self.array_config)
        if self.writeQueryLog:
            command.append('--writeQueryLog')
        return command

    @staticmethod
    def print_pseudo_command(command):
        #ChatGPT refactored code
        pseudo = []
        for arg in command:
            p = Path(arg)
            if p.exists():
                pseudo.append(p.name)
            else:
                pseudo.append(arg)
        print(f'executing command: {" ".join(pseudo)}')

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

    def determine_available_calibrators(self,work_folder):
        available_calibrators = {}
        cal_query_filepaths = self.get_cal_query_filepaths(work_folder=work_folder)
        for cal_type,filepath in cal_query_filepaths.items():
            if filepath.is_file():
                available_calibrators[cal_type] = self.read_available_calibrators(filepath)
        return available_calibrators

    def concatenate_cal_queries(self,work_folder):
        output_filepath = work_folder / f'{self.log_files_prefix}_calibrator_queries.txt'
        cal_query_filepaths = self.get_cal_query_filepaths(work_folder=work_folder)
        with open(output_filepath,'w') as outfile:
            for filepath in cal_query_filepaths.values():
                if filepath.is_file():
                    with open(filepath,'r') as infile:
                        outfile.write(infile.read())
                        outfile.write('\n\n######################################\n\n')
                    filepath.unlink()

    def move_log_files(self,work_folder):
        log_file_paths = self.get_log_file_paths(work_folder)
        for path in log_file_paths:
            shutil.move(src=path, dst=self.log_folder / f'HA{self.HA}h_{path.name}')

    def get_cal_query_filepaths(self,work_folder):
         return {cal:work_folder / f'{self.log_files_prefix}_{cal}_1.txt' for cal in
                 calibrator_query_identifiers}

    @staticmethod
    def read_available_calibrators(filepath):
        available_calibrators = []
        with open(filepath,"r") as file:
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
                    available_calibrators.append(calibrator)
        return available_calibrators

    def get_log_file_paths(self,folderpath):
        paths = folderpath.glob(f'{self.log_files_prefix}_*.txt') #iterator
        return list(paths)


class SBSimulation:

    def __init__(self,xml_path,log_folder,min_HA,max_HA,HA_step,obs_date,writeQueryLog,
                 array_config,check_array_config=True):
        self.xml_path = xml_path
        self.xml = OT_XML_File(filepath=xml_path)
        self.log_folder = log_folder
        self.min_HA = min_HA
        self.max_HA = max_HA
        self.HA_step = HA_step
        self.obs_date = obs_date
        self.writeQueryLog = writeQueryLog
        self.array_config = array_config
        if check_array_config:
            self.check_array_config()

    def check_array_config(self):
        nominal_configs = self.xml.get_nominal_configurations()
        if "7M" in nominal_configs:
            self.check_7M_config()
            return
        if "TP" in nominal_configs:
            self.check_TP_config()
            return
        self.check_12M_config(nominal_configs=nominal_configs)

    def check_7M_config(self):
        config = self.array_config
        requires_tp = self.xml.read_RequiresTPAntennas()
        requests_std_7m = config in ("default", "7M")
        requests_7m_with_tp = "aca" in config and "pm" in config

        if not requests_std_7m and not requests_7m_with_tp:
            ask_and_raise_error(
                f"WARNING: Do you really wish to simulate this 7m SB with "
                f"array configuration '{config}'?")
    
        if requires_tp and requests_std_7m:
            ask_and_raise_error(
                "WARNING: this 7M SB requires TP antennas, but requested "
                f"configuration '{config}' does not include TP antennas. Proceed?"
            )
    
        if not requires_tp and requests_7m_with_tp:
            ask_and_raise_error(
                "WARNING: this 7M SB does not require TP antennas, but it looks "
                f"like your requested configuration '{config}' might include TP. Proceed?"
            )

    def check_TP_config(self):
        if self.array_config not in ("default", "TP"):
            ask_and_raise_error(
                 f"WARNING: Do you really wish to simulate this TP SB with array configuration '{self.array_config}?'")

    def check_12M_config(self,nominal_configs):
        if (self.array_config.capitalize() not in nominal_configs
            and self.array_config != "default"):
            ask_and_raise_error(
                f"WARNING: Nominal configuration(s) of this SB: {nominal_configs}. Do "
                f"you really wish to simulate with configuration '{self.array_config}'?")

    def run(self):
        self.determine_HAs_to_simulate()
        #self.remove_existing_log_files()
        self.run_simulations()
        if self.writeQueryLog:
            self.summarize_available_calibrators()
        self.print_results()

    @staticmethod
    def DSA_HA_limits(dec):
        if dec.deg >= -5:
            return -3, 2
        else:
            return -4, 3

    def determine_HAs_to_simulate(self):
        rep_coord = self.xml.get_representative_coordinates()
        DSA_min_HA, DSA_max_HA = self.DSA_HA_limits(dec=rep_coord.dec)
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
        counter = 1
        while True:
            new_HA = min_HA + counter*self.HA_step
            if new_HA > max_HA:
                break
            self.HAs.append(new_HA)
            counter += 1

    def run_single_HA(self,HA):
        #IMPORTANT since this method is used inside executor.map for parallellisation,
        #it should only read, but not write to self. The reason is that if several
        #threads write to self at the same time, bad things might be happening...
        #Here we can clearly see that run_single_HA does not modify this class' attributes,
        #so everything is fine
        sim = SingleHASimulation(HA=HA, xml_path=self.xml_path,
                                 array_config=self.array_config,
                                 obs_date=self.obs_date,
                                 writeQueryLog=self.writeQueryLog,
                                 log_folder=self.log_folder)
        return sim.run()

    def run_simulations(self):
        #suggestion by AI: use ThreadPoolExecutor instead of ProcessPoolExecutor
        #since the heavy work is done by simulateSB.py, and this script only calls
        #simulateSB.py. Indeed, since I use subprocess.run, a separate process is
        #already created, so I only need separate threads here
        with ThreadPoolExecutor() as executor:
            output = list(executor.map(self.run_single_HA, self.HAs))
            self.results = [out[0] for out in output]
            if self.writeQueryLog:
                self.available_calibrators = [out[1] for out in output]

    def queried_calibrator_types(self):
        calibrator_types = []
        for available_cals in self.available_calibrators:
            calibrator_types += list(available_cals.keys())
        return list(set(calibrator_types))

    def summarize_available_calibrators(self):
        out_filename = self.log_folder / 'available_calibrators.csv'
        calibrator_types = self.queried_calibrator_types()
        #order the calibrator types according to the query order:
        calibrator_types = sorted(
                             calibrator_types,
                             key=lambda x:calibrator_query_identifiers.index(x))
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

    def append_results_to_file(self,filepath):
        with open(filepath,'a') as file:
            for HA,result in zip(self.HAs,self.results):
                file.write(f'{HA}h: {result}\n')


class Simulator:

    def __init__(self, args):
        #first, create objects to track all files and folders that are created. this
        #makes cleaning up easiser
        self.xml_filepaths = []
        self.created_log_folders = []
        self.created_summary_file = False
        #next handle input args:
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
        filepath = Path(filename)
        suffix = filepath.suffix
        if suffix == ".xml":
            self.input_mode = "xml"
            self.xml_filepaths.append(filepath)
        elif suffix == ".aot":
            self.confirm_aot_usage()
            self.input_mode = "aot"
            self.extract_xml_files_from_aot(filepath)
        else:
            raise ValueError("invalid arguments")

    def handle_code_sb_input(self, project_code, sb_name, array_config):
        self.array_config = array_config
        self.input_mode = "sb"
        filepath = Path(xml_filename(SB=sb_name))
        xml_path = OT_XML_File.download_xml_file(
            project_code=project_code,
            SB=sb_name,
            filepath=filepath,
        )
        print(f"downloaded {xml_path}")
        self.xml_filepaths.append(xml_path)

    def confirm_aot_usage(self):
        ask_and_raise_error(
            "ATTENTION: will use antenna configuration "
            f'"{self.array_config}" for ALL SBs of the project. '
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

    def aot_was_provided(self):
        return self.input_mode == "aot"

    def xml_was_provided_by_user(self):
        return self.input_mode == "xml"

    def extract_xml_files_from_aot(self,aot_file):
        print(f'going to extract xml files from {aot_file}')
        xml_pattern = 'Sch*.xml'
        old_xml_file_paths = list(Path.cwd().glob(xml_pattern))
        if len(old_xml_file_paths) > 0:
            raise RuntimeError('cannot extract xmls from .aot because some xmls'
                               +' already exist, please delete')
        subprocess.run(["unzip", str(aot_file), xml_pattern])
        extracted_xml_filepaths = Path.cwd().glob(xml_pattern)
        for xml_filepath in extracted_xml_filepaths:
            xml = OT_XML_File(xml_filepath)
            SB_name = xml.get_SB_name()
            new_xml_filename = xml_filename(SB=SB_name)
            new_path = xml_filepath.with_name(new_xml_filename)
            xml_filepath.rename(new_path)
            self.xml_filepaths.append(new_path)
        print(f'extracted following xml files: {self.xml_filepaths}')

    def prepare_log_folders(self):
        for xml_filepath in self.xml_filepaths:
            log_folder = Path(f'log_files_{xml_filepath.stem}')
            if log_folder.is_dir():
                remove_existing_log_folder = ask(
                            f'remove existing log folder {log_folder}?')
                if remove_existing_log_folder:
                    print(f'deleting folder {log_folder}')
                    shutil.rmtree(log_folder)
                else:
                    raise RuntimeError('aborting, please remove or rename existing log folder')
            log_folder.mkdir()
            self.created_log_folders.append(log_folder)

    def prepare_summary_file(self):
        self.summary_filepath = Path(f'{self.args.positional_args[0]}_simulation_summary.txt')
        if self.summary_filepath.exists():
            raise RuntimeError(f'{self.summary_filepath} already exits, please delete or rename')
        self.summary_filepath.touch()
        self.created_summary_file = True

    def run_simulations(self):
        for xml_path,log_folder in zip(self.xml_filepaths,self.created_log_folders):
            print(f'going to run simulations of {xml_path.name}')
            if self.aot_was_provided():
                with open(self.summary_filepath,'a') as file:
                    file.write(f'\n{xml_path.name}\n')
            #If aot file was provided, I already checked the array config, so
            #I do not need to do it again here
            check_array_config = not self.aot_was_provided()
            sb_sim = SBSimulation(
                        xml_path=xml_path,log_folder=log_folder,min_HA=self.args.min_HA,
                        max_HA=self.args.max_HA,HA_step=self.args.HA_step,
                        obs_date=self.args.obs_date,writeQueryLog=self.args.writeQueryLog,
                        array_config=self.array_config,check_array_config=check_array_config)
            sb_sim.run()
            if self.aot_was_provided():
                sb_sim.append_results_to_file(filepath=self.summary_filepath)
            print('\n------------------------------------------\n')

    def remove_created_xml_files(self):
        #want to remove xmls that are either downloaded or extracted from aot file
        if not self.xml_was_provided_by_user():
            for xml_path in self.xml_filepaths:
                xml_path.unlink()
                print(f'deleted {xml_path}')

    def remove_log_folders(self):
        for log_folder in self.created_log_folders:
            shutil.rmtree(log_folder)
            print(f'deleted {log_folder}')

    def remove_aot_summary_file(self):
        if self.created_summary_file:
            self.summary_filepath.unlink()
            print(f"deleted {self.summary_filepath}")

    def clean_up(self,keep_log_files):
        self.remove_created_xml_files()
        if not keep_log_files:
            self.remove_log_folders()
            self.remove_aot_summary_file()

    def print_log_file_info(self):
        log_folders_str = [str(lf) for lf in self.created_log_folders]
        print('log files can be found in following folder(s)): '
              +f'{", ".join(log_folders_str)}')
        if self.aot_was_provided():
            print(f'summary file: {self.summary_filepath}')

    def run(self):
        try:
            self.prepare_log_folders()
            if self.aot_was_provided():
                self.prepare_summary_file()
            self.run_simulations()
            keep_log_files = ask("keep log files?")
            self.clean_up(keep_log_files=keep_log_files)
            if keep_log_files:
                self.print_log_file_info()
        except Exception:
            self.clean_up(keep_log_files=False)
            raise


if __name__ == '__main__':
    xml = OT_XML_File('G022.25_a_09_7M_query.xml')