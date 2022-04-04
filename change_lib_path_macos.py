"""
    File name: move_exec.py
    Author: Jeremie Meurisse and Federico Semeraro
    Date created: 11/15/2021
    Date last modified: 11/15/2021
    Python Version: 3.9
"""

import os
from os import listdir
from os.path import isfile, join
import subprocess
import sys

### Functions
def get_files(path):
    """ Store all the file names in a list
    :param path: Path of the directory
    :return: return the list of file names
    """
    filelist = []
    for root, dirs, files in os.walk(path):
        for file in files:
            filelist.append(os.path.join(root,file)) #append the file name to the list
    return filelist

def get_folders(list):
    """ Get the folders of the executbles and libraries
    :param list: list of the executables/libraries
    :return: list of the folders
    """
    folders_list=[]
    for list_i in list:
        cmd="find $SRC_DIR -name "+list_i+" -type f | tail -n 1"
        folder=subprocess.Popen([cmd],shell=True, stdout=subprocess.PIPE).communicate()[0].decode("utf-8")
        folder=os.path.dirname(os.path.dirname(folder))
        folders_list.append(folder)
    return folders_list

def parse_otool_output(otool_output):
    """ Parse the output from otool -L
    :param otool_output: output from otool function
    :return: list of the libraries path
    """
    otool_output = otool_output.splitlines()
    out_paths = []
    extension=".dylib"
    for line in otool_output:
        if extension in line:
            ind = line.find(extension)
            out_paths.append(line[1:ind + len(extension)])

    return out_paths
    
def env_var_exists(env_var):
    """ Check if the environment variable exists
    :param env_var: environment variable name
    :return: environment variable value
    """
    env_value=os.environ.get(env_var)
    if env_value is None:
        print("Error: "+env_var+" does not exist.",file=sys.stderr)
        sys.exit()
    if not os.path.exists(env_value):
        print("Error: "+env_var+"=\""+env_value+"\" not found.",file=sys.stderr)
        sys.exit()
    return env_value

### Check if the SRC_DIR environment variable exists
src_dir=env_var_exists('SRC_DIR')

### Get folders of executables and libraries
list_exec=["blockMesh"] # OpenFOAM executable
dirs=get_folders(list_exec) # OpenFOAM prefix
sub_dirs=["bin","lib"]
of_index=list_exec.index("blockMesh")
of_platform_name=os.path.basename(dirs[of_index])

### Verify dirs
for i,dir_i in enumerate(dirs):
    if src_dir not in dir_i:
        print("Error: "+list_exec[i]+" not found.",file=sys.stderr)
        sys.exit()

### Change the path of the libraries
print("Running the loop...")
for i,dir_i in enumerate(dirs):
    for sub_dir_i in sub_dirs:
        my_path=dir_i+"/"+sub_dir_i
        files=get_files(my_path)
        my_path=my_path.replace(src_dir,"$SRC_DIR")
        print("Modify the path of the libraries in "+my_path)
        for file_i in files:
            file_i=file_i.replace(src_dir,"$SRC_DIR")
            cmd="otool -L " + file_i
            otool_output = subprocess.Popen([cmd],shell=True,stdout=subprocess.PIPE).communicate()[0].decode("utf-8")
            libs_path=parse_otool_output(otool_output)
            for lib_path_i in libs_path:
                if src_dir in lib_path_i:
                    file_name=os.path.basename(file_i)
                    lib_name=os.path.basename(lib_path_i)
                    new_file_path="@rpath/"+file_name
                    if lib_name == file_name:
                        cmd="install_name_tool -id "+new_file_path+" "+file_i
                    else:
                        dir_lib_j=os.path.basename(os.path.dirname(lib_path_i))
                        if dir_lib_j != "lib": # folder in sub_dir_i
                            new_path="@rpath/"+dir_lib_j+"/"+lib_name
                        else: # directly in sub_dir_i
                            new_path="@rpath/"+lib_name
                        cmd="install_name_tool -change " + lib_path_i + " " + new_path + " " + file_i
                    os.system(cmd)
            if ".o" not in os.path.basename(file_i):
                # Change rpath
                cmd="install_name_tool -add_rpath \"@executable_path/../lib\" "+file_i
                os.system(cmd)

print("End of the change_lib_path_macos.py script.")
