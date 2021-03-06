from time import sleep
import boto.ec2
import sys
import subprocess
import argparse
import os

# specify AWS keys
auth = {"aws_access_key_id": "<<add key>>", "aws_secret_access_key": "<<add secret access key>>"}

# create the connection object
conn = boto.ec2.connect_to_region("us-east-1", **auth)

# status of vms
instancefree={}

# status of projects evaluated. set it False for the projects which need to be evaluated
projects={}
projects['Chart']=True
projects['Closure']=True
projects['Lang']=False
projects['Math']=True
projects['Time']=True

# parameters required for launching experiment
faultlocflag="false"
startseed=1
endseed=20
startdefectid=1
enddefectid=2
testtype="allHuman"
genprogpath="/home/ubuntu/genprog4java"
defects4jpath="/home/ubuntu/defects4j"
testpercent=100

# parameters required for vm
alldone=False
vmcount=1
ami='<<add-ami>>' # also need to specify this in create_instances method
instancetype='<<add-type>>' # also need to specify this in create_instances method

# count of total #defects in a project plus one (values are based on current defects in defects4j dataset)
defects={}
defects['Chart']=27
defects['Closure']=134
defects['Lang']=66
defects['Math']=107
defects['Time']=28


def main():
	if len(sys.argv) < 2:
		create_script()
		print "Usage: python testexperiment.py {start|stop|terminate} path-to-key-file \n"
		sys.exit(0)
	else:
		action = sys.argv[1] 
		keypath = sys.argv[2]

	if action == "start":
		terminate_instances()
		sleep(30)
		delete_volumes()
		create_instances(keypath)
	elif action == "stop":
		stopInstances()
	elif action == "terminate":
		terminate_instances()
		sleep(30)
		delete_volumes()
	else:
		print "Usage: python experiment.py {start|stop|terminate} path-to-key-file \n"

# method to create instances
def create_instances(vm_key):
	# create instances. specify ami, key, type, min and max count
	instances_resv = conn.run_instances('<<add-ami>>',key_name='<<key name>>',instance_type='<<add-type>>',security_group_ids=[<<ids>>], min_count = 48, max_count = 48)
	print instances_resv
	print "number of instances created = ", len(instances_resv.instances)
	for i in instances_resv.instances:
		print "creating instance ", i.id
		while i.state == u'pending':						# wait until instance gets created
			print("Instance state: %s" % i.state)
		 	sleep(10)
		 	i.update()
		
   		global alldone	
	   	global vmcount
   		if projects['Closure'] and alldone: 				# if all experiments are launched and there are unused vms and unattached volumes then delete them
			conn.terminate_instances(instance_ids=[i.id])	
			delete_volumes()
		else:												# setup the instance
			setupInstance(i, vm_key)
			vmcount = vmcount + 1

	print("Instance state: %s" % i.state)
	print("Public dns: %s" % i.public_dns_name)
 	return i.public_dns_name

# method to setup an instance for running the experiment 
def setupInstance(i, vm_key):
	print "Starting instance", i.id
	if i.state == "stopped":
		i.start()
	
	while i.state == "pending":
		sleep(1)
		i.update()
      
	status=conn.get_all_instance_status(instance_ids=[i.id])
   	print "system status is: ",status[0].system_status.status, status[0].instance_status.status

   	# wait until instance is initialized and reachable
   	while status[0].system_status.status != 'ok' and status[0].instance_status.status != 'ok':
   		status=conn.get_all_instance_status(instance_ids=[i.id])
   		print "system status is: ",status[0].system_status.status, status[0].instance_status.status
		sleep(10)
   	print "instance started = ", i.id, " ip address is ", i.ip_address
   	instancefree[i.ip_address]=True

   	# launch experiment on instance
   	if i.ip_address != None and i.id!="i-10fa21c8":
		print "copying launch-repair script to ", i.ip_address
	   	do_scp(i.ip_address,"~/", vm_key)	

	   	print "set permissions of script on ", i.ip_address
	   	set_permissions(i.ip_address, vm_key)

	   	global startdefectid
	   	global enddefectid
	   	global alldone
	   	if not projects['Chart']: # launch 9 chart defects per vm on 3 vms (last vm has 8 defects)
			if startdefectid+9 < defects['Chart']:
				enddefectid=startdefectid+9
		   	else:
			   	enddefectid=defects['Chart']	
		   
		   	if instancefree[i.ip_address] is True:
				vmname="vm%s-Chart-%s-%s" %(vmcount, startdefectid, enddefectid)	   
		  	   	i.add_tag("Name", vmname)
		   	   	run(i.ip_address, vm_key, "Chart", startdefectid, enddefectid, "chart")		
			   	instancefree[i.ip_address]=False
	   	   	   	if enddefectid == defects['Chart']:
					projects['Chart'] = True
				   	startdefectid = 1
				   	enddefectid = 2
			   	else:
			   	   	startdefectid=enddefectid

		if not projects['Lang']: # launch 8 defects per vm on 8 vms (last vm has 9 defects)
		   	if startdefectid < 56 and startdefectid+8 < defects['Lang']:
				enddefectid=startdefectid+8
		   	elif startdefectid+9 == defects['Lang']:  #cond for last vm
			   	enddefectid=defects['Lang']
		   	else:
			   	enddefectid=defects['Lang']

		   	if instancefree[i.ip_address] is True:
			   	vmname="vm%s-Lang-%s-%s" %(vmcount, startdefectid, enddefectid)	
		  	   	i.add_tag("Name", vmname)
		   	   	run(i.ip_address, vm_key, "Lang", startdefectid, enddefectid, "lang")		
			   	instancefree[i.ip_address]=False
	   	   	   	if enddefectid == defects['Lang']:
					projects['Lang'] = True
				   	startdefectid = 1
				   	enddefectid = 2
			   	else:
					startdefectid=enddefectid

		if not projects['Time']: # launch 9 defects per vm on 3 vms
			if startdefectid+9 < defects['Time']:
				enddefectid=startdefectid+9
		   	else:
			   	enddefectid=defects['Time']	
		   
		   	if instancefree[i.ip_address] is True:
			   	vmname="vm%s-Time-%s-%s" %(vmcount, startdefectid, enddefectid)	   
		  	   	i.add_tag("Name", vmname)
		   	   	run(i.ip_address, vm_key, "Time", startdefectid, enddefectid, "time")		
			   	instancefree[i.ip_address]=False
	   	   	   	if enddefectid == defects['Time']:
					projects['Time'] = True
				   	startdefectid = 1
				   	enddefectid = 2
				else:
			   	   	startdefectid=enddefectid

		if not projects['Math']: # launch 7 defects per vm on 6 vms and 8 defects per vm on 8 vms
			if startdefectid < 43 and startdefectid+7 < defects['Math']:
				enddefectid=startdefectid+7 	
			elif startdefectid+8 < defects['Math']:
				enddefectid=startdefectid+8 	
			else:
				enddefectid=defects['Math']	
		   
		   	if instancefree[i.ip_address] is True:
				vmname="vm%s-Math-%s-%s" %(vmcount, startdefectid, enddefectid)	   
		  	   	i.add_tag("Name", vmname)
		   	   	run(i.ip_address, vm_key, "Math", startdefectid, enddefectid, "math")		
			   	instancefree[i.ip_address]=False
	   	   	   	if enddefectid == defects['Math']:
					projects['Math'] = True
				   	startdefectid = 1
				   	enddefectid = 2
			   	else:
			   	   	startdefectid=enddefectid


		if not projects['Closure']: # launch 7 defects per vm on 19 vms
			if startdefectid+7 < defects['Closure']:
				enddefectid=startdefectid+7
			else:
				enddefectid=defects['Closure']	
		   
		   	if instancefree[i.ip_address] is True:
			   	vmname="vm%s-Closure-%s-%s" %(vmcount, startdefectid, enddefectid)	  
		  	   	i.add_tag("Name", vmname)
		   	   	run(i.ip_address, vm_key, "Closure", startdefectid, enddefectid, "closure")		
			   	instancefree[i.ip_address]=False
	   	   	   	if enddefectid == defects['Closure']:
				   	projects['Closure'] = True
				   	startdefectid = 1
				   	enddefectid = 2
				   	alldone = True
			   	else:
			   	   	startdefectid=enddefectid

# method to shutdown instances 
def stopInstances():
   	print "stopping instances"
	reservations = conn.get_all_reservations()
	for reservation in reservations:
		for instance in reservation.instances:
			if instance.image_id == ami and instance.instance_type == instancetype and instance.state == "running":
				print "stopping instance ", instance.id
				instance.stop()

# method to terminate instances
def terminate_instances():
	print "terminating not required instances"
	reservations = conn.get_all_reservations()
	for reservation in reservations:
		for instance in reservation.instances:
			if instance.image_id == ami and  instance.instance_type == instancetype and instance.state == "stopped":
				print "terminating instance ", instance.id
				conn.terminate_instances(instance_ids=[instance.id])
   
# method to delete unattached volumes
def delete_volumes():
	for vol in conn.get_all_volumes():
		state = vol.attachment_state()
		if state == None:
			print vol.id, state
			print "deleting volume = ", vol.id
			conn.delete_volume(vol.id)

# method to run the script to launch an experiment on vm
def run(vmip, vm_key, project, startdefectid, enddefectid, folder):
	ssh_cmd = "ssh -o StrictHostKeyChecking=false -n -i %s ubuntu@%s \"nohup /bin/bash launch-repair.sh %s %s %s %s %s %s %s %s %s %s %s > /dev/null 2>&1 &\""
	ssh_str = ssh_cmd % (vm_key, vmip, project, startdefectid, enddefectid, folder, startseed, endseed, faultlocflag, genprogpath, defects4jpath, testtype, testpercent)
	print "executing script remotely using ", ssh_str	
	FNULL = open(os.devnull, 'w')
	return (subprocess.call(ssh_str,shell=True, stdout=FNULL, stderr=subprocess.STDOUT) == 0)

# method to copy the script to the instance
def do_scp(to_scp, where_scp, vm_key):
	script_path = "./launch-repair.sh"
	scp_script_cmd = "scp -o StrictHostKeyChecking=false -i %s %s %s ubuntu@%s:%s"
	scp_str = scp_script_cmd % (vm_key, vm_key, script_path, to_scp, where_scp)
	print "copying script and key file to vm using:", scp_str
	return (subprocess.call(scp_str,shell=True) == 0)

# method to set appropriate permissions to run the script
def set_permissions(vmip, vm_key):
	ssh_cmd = "ssh -o StrictHostKeyChecking=false -n -i %s ubuntu@%s \"chmod +x /home/ubuntu/launch-repair.sh\" &"
	ssh_str = ssh_cmd % (vm_key,vmip)
	print "setting permission on script remotely using ",ssh_str	
	return (subprocess.call(ssh_str,shell=True) == 0)

if __name__ == '__main__':
    main()
