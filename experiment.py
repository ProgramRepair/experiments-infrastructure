import subprocess
import argparse
import os
import re
import itertools
import time
from utils import *
from globals import *

# THIS IS NOT AS WELL TESTED AS IT MIGHT BE (since the refactor that added
# qemu!) 

# collect directive info for one directive file
def process_directive_files (filenames):
    global env_ht
    # blank and comment lines are allowed but skipped
    for filename in filenames:
        fin = open(filename,'r')
        lines = [ line.strip().split('=',1) for line in fin.readlines() \
                      if not((line[0] == '#') or (line.strip() == "")) ]
        fin.close()
        for (arg,arg_val) in lines:
            old = []
            if(env_ht.has_key(arg)):
                old = env_ht[arg]
            env_ht[arg] = appendf(old,arg_val)

# returns a list of the required arguments, the number of instances required,
# the number of currently running instances, and a list of arguments that have
# multiple definitions in the directive files
def setup ():
    # setup the workspace directory 
    global dirname
    dirname = "workspace." + envget("BATCH_NAME")
    if not os.path.exists(dirname):
        os.mkdir(dirname)

    # get required parameters, figure out how many instances are required
    script_template = open(template, 'r')
    req_regexp = re.compile("^export[\s]+([\w]+)[\s]*=[\s]*$")
    required = [ req_regexp.match(line).group(1) 
                 for line in script_template.readlines() 
                 if req_regexp.match(line) != None ]

    mult_func = lambda arg: len(env_ht[arg]) > 1
    num_desired = reduce((lambda x,y: x * y), 
                         [ len(env_ht[x]) for x in required])

    return required,num_desired,filter(mult_func, required)

# takes a list of required arguments (string list) and a list of
# multiply_defined arguments (also a string list)
# returns (int, (string * value) list) list; the int is an index/count
# scripts don't get written to disk until we actually launch them
# so as to be able to only write the ones we send (ideally)
def create_scripts (required,multiply_defined):
    not_multiply_defined = [ (x,env_ht[x][0]) for x in required if x not in multiply_defined ]
                             
    # all possible multiple parameter definitions
    lol2 = [ [ (x,value) for value in lst ] \
                 for x,lst in [ (x,env_ht[x]) for x in multiply_defined ]]

    my_extend = lambda combo: extendf(combo, not_multiply_defined)

    # add the non-multiply-defined arguments to each combination
    return [ my_extend(list(combo)) for combo in itertools.product(*lol2)]

def options():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', action='store', dest='num_attempts', \
                            help="Number of attempts to communicate per booted instance.",  \
                            default=10)
    parser.add_argument('-p', action='store', dest='premade_instances', \
                            help="file containing predefined instances.", \
                            default=None)
    parser.add_argument('-s', action='store', dest='size', \
                            help="instance size: small or medium.  Default: medium", \
                            default="medium")
    parser.add_argument('-c', action='store', dest='cloud', \
                            help="cloud: ec2 (Amazon AWS), euca (FG), or qemu (UNM).  Default: ec2", \
                            default="ec2")
    parser.add_argument('-t', action='store_true', dest='do_templates', \
                            help="also copy repair template experiment files.  Default: false", \
                            default=False)
    parser.add_argument('-w', action='store', dest='wait', \
                            help="how long to wait for instances to spin up.  Default: 360", \
                            default=360)
    parser.add_argument('directives', action='store', nargs='*')

    parse_results=parser.parse_args()

    process_directive_files([fname for fname in parse_results.directives])
    return parse_results

def prepare_scripts(scripts,addresses):
    global address_ht
    global port_ht
    stage_list = []

    script_template = '\n'.join([line.strip() for line in 
                                 open(template, 'r').readlines()])
    # prepare helper data for staging and write scripts to disk

    zipped = enumerate(zip(scripts[0:len(addresses)], addresses))

    for (count,(script,(instance,public,private,port))) in zipped:
        address_ht[count] = public
        port_ht[count] = port
        stage_list.append((count, Phase.WRAPPER_WAIT, 0))

        this_script = script_template
        for regexp, substr in [ (re.compile("export[\s]+" + arg + "[\s]*=[\s]*"), 
                                 "export " + arg + "=" + arg_val + "\n") 
                                for arg, arg_val in script ]:
            this_script= regexp.sub(substr, this_script)

        fout = open(dirname + "/" + str(count) + ".sh", 'w' )
        fout.write(this_script)
        fout.close()
    return stage_list

# instances is a list of string identifiers.
# returns (string * string * string) list; first string is the instance id,
# second is the public IP, third is run status

def ec2_get_addresses(instances):
    describe_instances_file = dirname + "/describe-instances.txt"
    hostnames_file = open(dirname + "/hostnames.txt", 'w')
    instance_list = ' '.join(instances)
    describe_str = "ec2-describe-instances " + instance_list 
    describe_proc = popen(describe_str)
    filter_lines = filter(is_instance, describe_proc.stdout)
    describe_fout = open(describe_instances_file,'w')
    for line in filter_lines: 
        describe_fout.write(line)
    describe_fout.close()
    hostnames = [ (line.split("\t")[1], line.split("\t")[3], "",22) for line in filter_lines ]
    for (instance,host,foo,bar) in hostnames:
        hostnames_file.write(instance + " " + host + "\n")
        print host
    hostnames_file.close()
    return hostnames

# instances is a list of string identifiers.
# returns (string * string * string) list; first string is the instance id,
# second is the public IP, third is run status
def euca_get_addresses(instances):
    addresses = [ ]
    for instance in instances:
        describe_proc = popen("euca-describe-instances " + instance)
        describe_line = filter(is_instance, describe_proc.stdout)[0].split("\t")
        addresses.append((instance,describe_line[3],describe_line[5],22))
    return addresses

# (string * string * string) list; instance id * port number * run status
# (running, by default)

def qemu_get_addresses(instances):
    addresses = [ ] 
    cur=os.getcwd()
    os.chdir("/nfs/adaptive/claire/many-bugs/")
    proc=popen("./bin/active-overlays")
    os.chdir(cur)
    for i in instances:
        print i
    lines=[line.strip().split(' ') for line in proc.stdout] 
    info=[(int(split[2]),split[-1]) for split in lines]
    info=[(i1,i2) for (i1,i2) in info if i1 != 0 ]
    for i in info:
        print i
    my_instances = [(port,name) for (port,name) in lines if name in instances ]
    return [(name,"localhost","running",int(port)) for (port,name) in my_instances ]

# takes the number of instances we want
# returns a list of instance string identifies 
# FIXME: add error handling!
# saves the run instance info to dirname/run-instances.txt
# saves the instance list to dirname/instances.txt
# note that the size parameter is misleading, here, because I don't actually use
# it anywhere and instead just hardcoded c1.medium as instance type.
def ec2_launch_instances (num_desired,size):
    run_instances_file = dirname + "/run-instances.txt"
    instance_list_file = dirname + "/instances.txt"
    # Note: (A) we currently don't check for BASE_AMI as a required argument,
    # and (B) the key (genprogkey), the instance type (c1.medium), the shutdown
    # behavior (terminate) and the prefix to the client-token
    # (genprog-idempotent) here are hard-coded.  Most of them shouldn't be.  
    shell_str = "ec2-run-instances " + envget("BASE_AMI") + " -n " + str(num_desired) + \
        " -k genprogkey -t c1.medium --availability-zone " + envget("AVAIL_ZONE") + \
        " --instance-initiated-shutdown-behavior terminate " + \
        " --client-token genprog-idempotent-" + envget("BATCH_NAME") + \
        " >& " +  run_instances_file

    if(subprocess.call(shell_str,shell=True) == 0):
        # print out the output for debugging
        fout = open(run_instances_file, 'r')
        file_lines = fout.readlines()
        fout.close()
        instances = instances_conv(file_lines)
        # annoying that this 
        counter = 1
        for instance in instances:
            name=envget("BATCH_NAME") + "-" + str(counter)
            counter += 1
            tag_str = "ec2-create-tags %s --tag Name=%s" % (instance, name)
            subprocess.call(tag_str,shell=True)
        return instances
    else: 
        print "ERROR: call to ec2-run-instances failed, exiting"
        exit(1)

def euca_launch_instances (num_desired,size):
    shell_str = "euca-run-instances -k " + env_ht["VM_KEY"][0] + " -n " + \
        str(num_desired) + " -t m1." + size + " " + env_ht["BASE_AMI"][0]
    instance_proc = popen(shell_str)

    stdout = instance_proc.stdout
    # print out the output for debuggnig
    fout = open(dirname + "/run-instances.txt", 'w')
    file_lines = []
    for line in stdout:
        file_lines.append(line)
        fout.write(line)
    fout.close()
    return instances_conv(file_lines)


def qemu_launch_instances (num_desired,size):
    pwd_str = "/nfs/adaptive/claire/many-bugs"
    disk = "genprog_icse2012_aws/genprog_icse2012_fedora13.raw"
    # maybe make "disk" the previous "BASE_AMI"? 

    # OK, to make a qemu instance, we need to make an overlay (sort of like
    # tagging in ec2) and then launch the new machine on an open port assuming
    # for now that a given overlay is *not* already running.  FIXME: ERROR THE
    # HANDLING
    cur=os.getcwd()
    os.chdir("/nfs/adaptive/claire/many-bugs/")
    proc=popen("./bin/active-overlays")

    lines = [ line.strip().split(' ') for line in proc.stdout ]
    info=[(int(split[0]),int(split[2]),split[-1]) for split in lines ]

    os.chdir(cur)
    port_used = lambda (i1,i2,i3): int(i2) != 0
    in_use=[port for (i1,port,i3) in filter(port_used,info) ]

    ports=[]
    port = 2222

    while len(ports) < num_desired:
        if port not in in_use:
            ports.append(port)
        port += 1

    counter = 0
    cur=os.getcwd()
    os.chdir(pwd_str + "/overlays")
    instances=[]

    for port in ports:
        name=envget("BATCH_NAME") + "-" + str(counter) +".qcow2"
        counter += 1
        instances.append((name,port))
        if not os.path.exists(pwd_str + "/overlays/" + name):
            # make an overlay for each desired instance
            cmd="qemu-img create -b ../%s -f qcow2 %s" % (disk,name)
            subprocess.call(cmd,shell=True)

    os.chdir(pwd_str)
    for (name,port) in instances:
        base_cmd = \
            "qemu-system-x86_64 -kernel genprog_icse2012_aws/vmlinuz-2.6.34.9-69.fc13.i686.PAE -initrd genprog_icse2012_aws/initramfs-2.6.34.9-69.fc13.i686.PAE.img -hda %s/overlays/%s  -append 'root=/dev/sda' -m 2G -net nic -net user,hostfwd=tcp:127.0.0.1:%d-:22 -nographic -daemonize"
        full_cmd = base_cmd % (pwd_str,name,port)
        run_proc=subprocess.call(full_cmd,shell=True)
    os.chdir(cur)
    return [name for name,port in instances ] 

def qemu_check_done(instances,addresses):
    return [],addresses

def euca_check_done(instances,addresses):
    return partition(is_done,addresses)

# FIXME: did I break EC2?  TEST THE HELL OUT OF IT BEFORE LAUNCHING ALL THE
# THINGS
def ec2_check_done(instances,addresses):
    really_done = [ i for (i,a,foo,bar) in addresses ] 
    not_done = [ i for i in instances if i not in really_done ]
    return not_done,addresses

launch_instances = {
    "qemu" : qemu_launch_instances,
    "euca" : euca_launch_instances,
    "ec2" : ec2_launch_instances
} 

get_addresses = {
    "qemu" : qemu_get_addresses,
    "euca" : euca_get_addresses,
    "ec2" : ec2_get_addresses
}
    
check_done = {
    "qemu" : qemu_check_done,
    "euca": euca_check_done,
    "ec2" : ec2_check_done
}

# takes an integer (num desired) and a string name for premade instance list (if
# it exists), or it's None
# returns a list of (instance * public * private/status * port) tuples 
# checks addresses/assigns them even if premade
def get_instances (num_desired,premade,size,wait):
    global dirname

    instances = []
    efforts=0
    # get predefined instances
    if(premade != None):
        instances = [line.strip() for line in open(premade).readlines() ]
        if(len(instances) > num_desired):
            instances = instances[0:num_desired]
    if(len(instances) < num_desired):
        num_desired = num_desired - len(instances)
        instances.extend(launch_instances[cloud](num_desired,size))

    # debug output
    fout = open(dirname + "/instances.txt", 'w')
    for instance in instances:
        fout.write(instance + "\n")
    fout.close()

    time.sleep(wait)

    addresses = get_addresses[cloud](instances)
    not_done,done = check_done[cloud](instances,addresses) 

    while(len(not_done) > 0 and efforts < 10): # FIXME: hard coded
        time.sleep(30)
        addresses = get_addresses[cloud](i for (i,p,s,pp) in not_done)
        not_done,done1 = check_done[cloud](instances,addresses)
        done.extend(done1)
        efforts += 1
    return done,not_done


# FIXME: indicate when this doesn't work (num attempts times out)?


# stage takes a list of things to stage, the hashtable with their addresses
# (indexed by instance count), a list of instance,stage,attempt tuples that have
# been staged successfully, and a list of inastance counts on which we gave up,
# and returns the successfully staged instances and the given_up list


def get_key():
    if cloud == "euca":
        return envget("VM_KEY") + ".pem"
    else:
        return envget("VM_KEY")

def do_scp(count,to_scp,where_scp):
    scp_something = \
        "scp -P %d -o StrictHostKeyChecking=false -i %s %s root@%s:%s"
    vm_key=get_key()
    scp_str = scp_something % (port_ht[count],vm_key,to_scp,address_ht[count],where_scp)
    return (subprocess.call(scp_str,shell=True) == 0)

# Stage stages the experiments on each machine.  Because VMs can spin up at
# different rates, and scping all the files at once can arbitrarily fail, it
# uses a baby state machine per experiment being staged to make sure all the
# pieces are successfully copied over.  
def stage(stage_list, done):
    if (len(stage_list) == 0): 
        return done
    else:
        new_stage_list = []
        for count,phase,attempts in stage_list:
            if(phase == Phase.WRAPPER_WAIT):
                # copy the keyfile to scp results, the keyfile to get things
                # from the host, and the experiment-machine-script-wrapper.sh
                to_scp = \
                    envget("RESULTS_KEYFILE") + " " + envget("HOST_KEYFILE") + " experiment-machine-script-wrapper.sh" 
                if(do_scp(count, to_scp,"")):
                    new_stage_list.append((count,Phase.SCRIPT_WAIT,0))
                elif (attempts < num_attempts):
                    new_stage_list.append((count,phase,attempts+1))

            elif (phase == Phase.SCRIPT_WAIT):
                to_scp = dirname + "/" + str(count) + ".sh"
                if(do_scp(count,to_scp,"experiment-machine-script.sh")):
                    if(do_templates):
                        new_stage_list.append((count,Phase.TEMPLATES_WAIT,0))
                    else:
                        done.append((count,0))
                elif(attempts < num_attempts):
                    new_stage_list.append((count,phase,attempts+1))

            elif (phase == Phase.TEMPLATES_WAIT):
                if(do_scp(count,"templates.h","")):
                    to_scp = envget("BENCHMARK") + "-templates.c"
                    if(do_scp(count,to_scp,"templates.c")):
                        done.append((count, 0))
                    elif(attempts < num_attempts):
                        new_stage_list.append((count, phase, attempts + 1))
                elif(attempts < num_attempts):
                    new_stage_list.append((count, phase, attempts + 1))
        return stage(new_stage_list, done)

# note the hard-coded root@ username below; need to change for G4J experiments.    
def run(to_run):
    ssh_cmd = \
        "ssh -p %d -o StrictHostKeyChecking=false -n -i %s root@%s \"/bin/bash experiment-machine-script-wrapper.sh\" &> %s/%d.log"

    if len(to_run) > 0:
        new_to_run = []
        for (count,attempts) in to_run:
            ssh_str = \
                ssh_cmd % (port_ht[count], get_key(), address_ht[count], dirname, count)
            if(subprocess.call(ssh_str,shell=True) == 0): # FIXME: why is this "== 0" and not " != 0"?
                if(attempts < num_attempts):
                    new_to_run.append((count,attempts + 1))
        run(new_to_run)
    

def main():
    global cloud
    global num_attempts
    global do_templates

    parse_results=options()

    cloud=parse_results.cloud
    num_attempts=parse_results.num_attempts
    do_templates=parse_results.do_templates

    wait=float(parse_results.wait)
    if cloud == "qemu":
        wait=0.0

    required_args,num_to_create,multiply_defined = setup()

    scripts=create_scripts(required_args,multiply_defined)

    addresses,failed_addresses = \
        get_instances(num_to_create,parse_results.premade_instances, \
                          parse_results.size, wait)

    stage_list = prepare_scripts(scripts,addresses)
    to_run = stage(stage_list,[])
    run(to_run)

    # It would be very easy to print out the missing experiment scripts here
    print "The following instances failed to get addresses, kill them!"
    for (i,s,p) in failed_addresses:
        print i

main ()

