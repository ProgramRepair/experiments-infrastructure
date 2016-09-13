# This script is used to test if experiment finished successfully and identify the summarized reparability results 

import commands

command = "find . -wholename \"./*Buggy\" | wc -li"
status, output1 = commands.getstatusoutput(command)
if status is 0:
	print "total defects executed: ", output1
	command = "find . -wholename \"./*Buggy/log*Seed20.txt\" | wc -l"
	status, output2 = commands.getstatusoutput(command)
	if status is 0:
        print "total defects executed successfully: ", output2

if output1 != output2:
	l1=[]
	l2=[]
	command1 = "find . -wholename \"./*Buggy_1\""
	status, output1 = commands.getstatusoutput(command1)
	output1 = output1.split('\n')
	for d in output1:
		d = d.split('/')[1]
		if d not in l1:
			l1.append(d)
	command2 = "find . -wholename \"./*Buggy_1/log*Seed20.txt\""
	status, output2 = commands.getstatusoutput(command2)
	output2 = output2.split('\n')
	for d in output2:
		if '/' in d:
			d = d.split('/')[1]
			if d not in l2:
				l2.append(d)
	print "re-reun experiment for following defects"
	print list(set(l1) - set(l2))
else:
	print "experiment successful"

command = "grep \"Repair\" -r ./*/log*.txt"
status, output = commands.getstatusoutput(command)
defects_repaired = []
reparability_info = {}
seed_count = {}

if status is 0:
	output = output.split('\n')
	for grepout in output:
		grepout = grepout.split('/')
		defect = grepout[1].replace("Buggy", "").strip()
		details = grepout[2].split(".txt:Repair Found:")
		seed = details[0].replace("log%s"%(defect.title()),"").strip()
		variant = details[1].strip()
#		print "%s\t%s\t%s" %(defect, seed, variant)
		if defect not in defects_repaired:
			defects_repaired.append(defect.strip())
		if defect not in reparability_info:
			reparability_info[defect]= "%s variant %s"%(seed,variant)
			seed_count[defect]=1
		else:
			existing_info = reparability_info[defect]
			reparability_info[defect] = "%s :: %s variant %s" %(existing_info,seed,variant)
			seed_count[defect]= seed_count[defect]+1

print "Total #defects repaired", len(defects_repaired)
for defect in defects_repaired:
	print defect, "\t", seed_count[defect], "\t", reparability_info[defect]
