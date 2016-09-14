#############
# this script checks the full-repair/fault localization results for defects4j dataset
# this is supposed to be run from inside the repair-results folder on RESULT-SERVER
# way to run: python gettestresults.py
# enter 1 to get fault-localization testing results and 2 to get full repair testing 
# results
############
import commands

testtype = raw_input("Enter test-type (1-Fault localization testing, 2-Full repair testing): ")

if testtype == 1:
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
		command1 = "find . -wholename \"./*Buggy\""
		status, output1 = commands.getstatusoutput(command1)
		output1 = output1.split('\n')
		for d in output1:
			d = d.split('/')[1]
			if d not in l1:
				l1.append(d)
	
		command2 = "find . -wholename \"./*Buggy/log*Seed20.txt\""
		status, output2 = commands.getstatusoutput(command2)
		output2 = output2.split('\n')
		for d in output2:
			if '/' in d:
				d = d.split('/')[1]
				if d not in l2:
					l2.append(d)
		print "experiment failed for following defects"
		print list(set(l1) - set(l2))
	else:
		print "experiment successful"
else:
	defects=['Chart', 'Closure', 'Lang', 'Math', 'Time']
	for defect in defects:
		defectstr="verifying %s output" %(defect)
		print defectstr
		cmd1 = "find . -name \"%s*Buggy\" | wc -l" %(defect.lower())
		cmd2 = "find . -wholename \"./%s*Buggy/log%s*Seed1.txt\" | wc -l" %(defect.lower(), defect)
		cmd3 = "grep \"Fault localization was peprformed successfully\" -r ./%s*/log%s*Seed1.txt | wc -l" %(defect.lower(), defect)
		status1, output1 = commands.getstatusoutput(cmd1)
		status2, output2 = commands.getstatusoutput(cmd2)
		status3, output3 = commands.getstatusoutput(cmd3)
		print "total defects executed:", output1 
		print "total defects executed successfully:", output2 
		print "total defects where fault localization was successful:", output3
		if output1 == output2 and output2 == output3:
			print "PASS"
			print
		else:
			l0=[]
			l1=[]
			l2=[]
			cmd1 = "find . -name \"%s*Buggy\"" %(defect.lower())
			cmd2 = "find . -wholename \"./%s*Buggy/log%s*Seed1.txt\"" %(defect.lower(), defect)
			cmd3 = "grep \"Fault localization was peprformed successfully\" -r ./%s*/log%s*Seed1.txt" %(defect.lower(), defect)
			status1, output1 = commands.getstatusoutput(cmd1)
			status2, output2 = commands.getstatusoutput(cmd2)
			status3, output3 = commands.getstatusoutput(cmd3)
			
			output1 = output1.split('\n')
			for d in output1:
				d = d.split('/')[1]
				if d not in l0:
					l0.append(d)

			output2 = output2.split('\n')
			for d in output2:
				d = d.split('/')[1]
				if d not in l1:
					l1.append(d)
	
			output3 = output3.split('\n')
			for d in output2:
				if '/' in d:
					d = d.split('/')[1]
					if d not in l2:
						l2.append(d)
			print "FAIL"
			print "fault localization failed for following defects"
			if len(l0) != len(l1):
				print list(set(l0) - set(l1))
			else:	
				print list(set(l1) - set(l2))
			print
