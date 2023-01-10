import os
import yaml
from sys import argv
from datetime import datetime
from pathlib import Path
from netmiko import ConnectHandler
from netmiko.ssh_exception import NetMikoTimeoutException, SSHException
from jinja2 import Environment, FileSystemLoader
from openpyxl import load_workbook

#######################################################################################
# ------------------------------                   -----------------------------------#
#######################################################################################

helper = {
    "kyzy": ["172.20.50.22", "172.20.24.170"],
    "alma": ["172.20.17.181", "172.20.17.209", "172.20.24.170", "172.20.0.178"],
    "shim": ["172.20.18.117", "172.20.24.170"],
    "tara": ["172.20.22.157", "172.20.22.161", "172.20.24.170"],
    "seme": ["172.20.14.33", "172.20.24.170"],
    "ural": ["172.20.12.33", "172.20.24.170"],
    "akta": ["172.20.15.33", "172.20.24.170"],
    "kost": ["172.20.11.33", "172.20.24.170"],
    "asta": ["172.20.26.14", "172.20.19.9", "172.20.24.170"],
    "koks": ["172.20.9.33", "172.20.24.170"],
    "petr": ["172.20.10.33", "172.20.24.170"],
    "pavl": ["172.20.36.54", "172.20.24.170"],
    "ustk": ["172.20.46.37", "172.20.24.170"],
    "kara": ["172.20.34.2", "172.20.24.170"],
    "akto": ["172.20.28.2", "172.20.24.170"],
    "atyr": ["172.20.30.38", "172.20.24.170"]
    }

conf_dic = {
    "helpers": None,    # ["172.20.14.33", "172.20.24.170"]
    "vlans": None,      # [1010 1011 1012 .. 1015]
    "port": None,       # BS port
    "ip": None,         # list of bs ip
    "mask": None,
    "ios_type": None,
    }

configuration_log = []


#######################################################################################
# ------------------------------ def function part -----------------------------------#
#######################################################################################


def get_arguments(arguments):
    cfg = False
    for arg in arguments:
        if arg == "cfg" or arg == "CFG" or arg == "conf":
            cfg = True
    print("\n"
         f"config mode:...................{cfg}\n")
  
    return cfg


def get_user_pw():
    with open("psw.yaml") as file:
        user_psw = yaml.load(file, yaml.SafeLoader)

    return user_psw[0], user_psw[1]


def get_info():

    device = input("Enter device (ip or hostname): ")
    region = device.split("-")[0]
    
    if "." in region:
        region_final = region.split(".")[1]
    else:
        region_final = region    

    return region_final, device


def set_region(conf_dic, probable_region):

    while True:
        region = input(f"Enter region [{probable_region}]: ") or probable_region
        if helper.get(region):
            break
        else:
            print("wrong region. enter one of:\n\
                kyzy, alma, shim, tara, seme, ural, akta, kost\n\
                asta, koks, petr, pavl, ustk, kara, akto, atyr")

    conf_dic["helpers"] = helper[region]


def set_ios(conf_dic, device):
    
    if "csg" in device:
        ios_type = input("Enter ios (ios,xr,xe) [ios]: ") or "ios"
    elif "pagg" in device:  
        ios_type = input("Enter ios (ios,xr,xe) [xr]: ") or "xr"
        
    if ios_type == "ios":
        conf_dic["ios_type"] = "cisco_ios"
    elif ios_type == "xr":
        conf_dic["ios_type"] = "cisco_xr"
    elif ios_type == "xe":
        conf_dic["ios_type"] = "cisco_xe"


def connect(usr, psw, conf_dic, device):

    ssh_conn = ConnectHandler(device_type=conf_dic["ios_type"], ip=device, username=usr, password=psw)
    show_inf_desc = ssh_conn.send_command("show interfaces description")

    return ssh_conn, show_inf_desc


def define_port_vlan(show_inf_desc, conf_dic):
    
    if conf_dic["ios_type"] == "cisco_ios":
        vl = []     # 101 102 103
        probable_last_vlan = "1010"
        
        print("########################################\n"
             f"{show_inf_desc}\n"
              "########################################")
        
        for line in show_inf_desc.splitlines():
            if "Vl10" in line:
                vl.append(line.split()[0][2:5])     #Vl1010 -> 101
        
        if len(vl) > 1:
            last_vlan = vl[-1]
            probable_last_vlan = str(int(last_vlan)+1) + "0"
            
        vlan = input(f"Enter first vlan (1010,1020,..,10x0) [{probable_last_vlan}]: ") or probable_last_vlan
        vlans = [str(int(vlan)+i) for i in range(6)]
        conf_dic["vlans"] = vlans
         
    conf_dic["port"] = input("Enter BS interface: ")
    

def load_excel(conf_dic):
    cwd = os.getcwd()
    files = []
    for i in os.listdir(cwd):
        if os.path.isfile(i) and "xlsx" in i:
            files.append(i)

    print(f"xlsx files in current directory: [{', '.join(files)}]")	
    
    probable_file = files[0]
    
    excel_file = input(f"Enter BS excel file [{probable_file}]: ") or probable_file
    ip_list = []

    wb = load_workbook(excel_file)
    first_sheet = wb.sheetnames[0]
    sheet = wb[first_sheet]

    x = 1
    y = 1

    while True:
        v = sheet.cell(row=x, column=y).value
        if "." in str(v) and len(v.split(".")) == 4:
            last_octet1 = v.split(".")[3]
            
            v2 = sheet.cell(row=x, column=y+1).value
            v3 = sheet.cell(row=x, column=y+2).value
            
            if "." in str(v2) and "." in str(v3):
                last_octet2 = v2.split(".")[3]
                if int(last_octet1) + 1 == int(last_octet2):
                    ip = sheet.cell(row=x, column=y).value
                    mask = sheet.cell(row=x, column=y+2).value
                    ip_list.append(ip)
            
        y += 1
        if y == 60:     # max limit
            y = 1
            x += 1

        if len(ip_list) == 6:     # max limit
            break
            
        if x == 30:     # max limit
            print("########################################"
                 f"# ERROR check IP: {ip_list}")
            break
    
    if len(ip_list) != 6:
        print("########################################"
             f"# ERROR check IP: {ip_list}")

    conf_dic["ip"] = ip_list
    conf_dic["mask"] = mask


def read_template(conf_dic):
    
    template_output = ""
    
    if conf_dic["ios_type"] == "cisco_ios":
        env = Environment(loader=FileSystemLoader('./'))
        template = env.get_template("csg-template.txt")
        template_output = template.render(config = conf_dic)
        
    return template_output.splitlines()
 

def configure(ssh_conn, commands, configuration_log, cfg):

    if cfg:
        if len(commands) > 0:
            configuration_log.append(ssh_conn.send_config_set(commands))
            
            try:
                configuration_log.append(ssh_conn.save_config())
            except Exception as err_msg:
                configuration_log.append(f"COMMIT is OK after msg:{err_msg}")
                configuration_log.append(ssh_conn.send_command("\n", expect_string=r"#"))
            
        else:
            print("########################################"
                  "cfg is not needed")
    else:
        if len(commands) > 0:
            print("########################################")
            for line in commands:
                print(line)


def check_commit(configuration_log, commands, cfg):

    if cfg:
        for i in configuration_log:
            if "%" in i:
                print("########################################\n"
                    "ERROR. CFG-COMMIT")

        for j in commands:
            if "!" not in j and "" != j and "no shutdown" not in j:
                if j not in "".join(configuration_log):
                    print("########################################\n"
                        "ERROR. Not all config is loaded. Check cfg log")

def write_logs(cfg):

    start_time = datetime.now()
    current_date = start_time.strftime("%Y.%m.%d")
    current_time = start_time.strftime("%H.%M")

    log_folder = Path(f"{Path.cwd()}/logs/{current_date}/")  # current dir / logs / date /
    log_folder.mkdir(exist_ok=True)
    
    config = log_folder / f"{current_time}_configuration_log.txt"
    config_file = open(config, "w")
    
    if cfg and commands:
        config_file.write("#" * 80 + "\n")
        config_file.write(f"########################################\n\n")
        config_file.write("".join(configuration_log))
        config_file.write("\n\n")

    config_file.close()
    if not cfg:
        config.unlink()         

#######################################################################################
# ------------------------------              ----------------------------------------#
#######################################################################################

print(
    "\n"
    "---------------------------------------------------------------------------"
)

cfg = get_arguments(argv)
username, password = get_user_pw()
region, device = get_info()
set_region(conf_dic, region)
set_ios(conf_dic, device)

try:
    ssh_conn, show_inf_desc = connect(username, password, conf_dic, device)
except:
    ssh_conn = False
    print("########################################\n"
          "connection error\n"
          "########################################")
    
if ssh_conn: 
    define_port_vlan(show_inf_desc, conf_dic)
    load_excel(conf_dic)
    commands = read_template(conf_dic)
    configure(ssh_conn, commands, configuration_log, cfg)
    ssh_conn.disconnect()
    write_logs(cfg)
    check_commit(configuration_log, commands, cfg)

    print("########################################\n"
          "success\n"
          "########################################")
    