import re
from utils import *

# global vars used in all the experiment setup stuff
Phase = enum(WRAPPER_WAIT=1, SCRIPT_WAIT=2, TEMPLATES_WAIT=3, RUN_WAIT=4, DONE=5, GIVENUP = 6)
template="experiment-machine-script-template.sh"
dirname="./"
env_ht = {}
cloud = "euca"
is_done = lambda (instance,public,status,port): (status == "running" and not public.startswith("server-"))
num_attempts = 10

def envget(arg):
    return env_ht[arg][0]

instance_regexp = re.compile("^INSTANCE[\s]+")
is_instance = lambda line: instance_regexp.match(line) != None
instances_conv = lambda lines: [ line.strip().split("\t")[1] \
                                    for line in lines if instance_regexp.match(line) != None ]

address_ht = {}
port_ht = {}
do_templates = False
