# experiments-infrastructure
Scripts and other support for launching and managing large-scale repair
experiments on a cloud infrastructure (usually EC2). 

### disclaimer(s)

The existing set of scripts is a huge kludge that was never intended to survive
as long as it has.  I look forward to generalizing it and improving its design,
usability, and maintainability.

(I use CGenprog to refer to the GenProg4C code and G4J for GenProg4Java
throughout this explanation.)

### somewhat relevant history

The current scripts in this repository are taken from a private svn repository
(hosted at UVA).  These scripts have been used to launch and manage repair
experiments across many virtual machines in one of several cloud frameworks.
The most robust and best-tested and most widely used of these modes is EC2,
though the protocol was roughly the same for all of them.

### Design decisions

Throughout my explanation, I've stumbled upon various design points in
generalizing this setup for G4J.  I am trying to document them as I find them,
in one place; I refer to them in context by their tags here where they apply in
the subsequent explanation (if applicable).

(D1) One or many set of driver scripts? 

We can either generalize the approach to work across many different types of
repair experiment launches (GenProg4Java vs GenProg4C) or instantiate two sets
of scripts, one for Java and one for C.  I propose something close to the former
approach, with customization; more suggestions below.  CLG anticipates we can
remove (or simply not re-implement) support for the other cloud types besides EC2 moving
forward, regardless of which way we go.

(D2) Where to get defects4j and g4j, which version should they be set to, and
how will we keep track?

The original CGenProg experimental scripts were setup such that the scenarios to
be repaired and the version of CGenProg to use to repair them (as a compiled
binary) were hosted on a separate server.  On experiment initiation, the scripts
controlling the experiment copy those files over from the host machine to the
VM.

Our VM has defects4j and G4J checked out already on them, so this seems
unecessary.  However, it provides a benefit in the sense that we can be very
certain which version of a defect and which version of the repair code were used
in a particular experimental run. 

Regardless, it is imperative that we save which version of Defects4J and G4J we
use in any particular run in the experimental log, to enable reproducibility. 

(D3) Robustness in experiment launching, part 1.  Experiments involve launching
a large number of VMs.  Turns out that no cloud system can successfully always
spin up 100s of VMs at a time and have every one actually succeed.  If not all
VMs launch successfully, the driver script launches experiments on the ones that
*do* spin up and prints an error message about those that didn't succeed,
telling the user to kill those instances (which are usually zombies) and then
presumably try again to launch the missing experimental runs.  Figuring out
which runs those are is a manual process; it relies on the fact that experiments
are launched in sequence and the individual scripts that launch the experiments
are numbered.  So if I saw that 2 instances in a launch that should have created
10 failed to launch, I knew that that meant the last 2 scripts (9.sh and 10.sh)
didn't launch, and so the experimental parameters they were instantiated with
correspond to the missing run (because of coincidental ordering, this usually
just means the last two seeds).

This is not an amazing process.

Part 2: each of stage, copy, and run can fail if a given virtual machine
instance croaks.  The script tries some hard-coded (possibly an optional
argument?) number of times and prints out some information on those that fail.
Usually I find that VMs fail early, however, so I'm not certain what kind of
output is provided here.  

Regardless, the "capped number of repeated attempts" thing is absolutely
necessary for robustness; what can be improved is support for launching the
desired experiments that failed and debug output. 

### High-level Workflow

Here's the general idea: the user specifies the scenario name, configuration
file and any arguments to pass to CGenProg, and each random seed on which she
wants it to be run.  The script launches one VM per seed on which genprog will
be run; and then creates a script to conduct the actual run, copies it over to a
VM, and launches it remotely. More on that in a minute.

### experiment-machine-script-template.sh: A single experiment script 

Let's start with what happens on a single virtual machine, to which a script is
copied and then launched.

This launched script is instantiated from experiment-machine-script-template.sh
(in this repos).  The instantiated script is copied over to each VM such that
it's called "experiment-machine-script.sh" on that end.

Creating the script involves instantiating a new version of it based on the
template and desired experimental parameters, filling in missing parts. The
parts that need to be filled in are the "empty" exports at the top (export
BATCH_NAME=, export TARBALL=, etc).  Those exported variables are required to
instantiate the script and so if you don't provide them in a directive file (see
below), the setup gives up.

The work starts around line 55 of experiment-machine-template.  It does a few
things to set up -- it changes permissions on the key files, prints out some
useful information.  The part about "overcommit_ration and overcommit_memory",
at least on the Fedora machines we were running before, were necessary because
there is/was no swap on cloud compute instances, and so we only had access to
50% of memory at a time.  I don't know if it works on ubuntu or if the files are
in the same place; someone needs to check.  I assume it's still required,
though.

The "sleep shutdown_timeout" on line 70 serves to kill experiments that have not
yet completed on their own after some (user-specified) period of time. 

The script then does some sanity checking to make sure necessary key files and
directories are found.  Switching to G4J, we'll still need to check for
necessary keyfiles (which ones we need may change), but presumably not the
genprog-many-bugs directory.

At line 87, it copies a tarball of the scenario over from a specified host
machine and directory.  This part needs to change because we're setting up the
scenarios differently, by updating or acquiring g4j and defects4j (D2) and
calling a script to setup the particular scenario we want to try to repair
(which will need to be user specified, so added to the exports at the top, if we
follow the current paradigm), presumbly from the g4j repository.

If defects4j or g4j are either not present on the machine or not available to be
copied over or checked out, this should be considered a failure.

What we did for CGenProg was copy a particular executable over from a specified
host machine (~ line 99 of script template),  to ensure that
all experiments were run using the same executable.  We could take this approach
for G4J, if we want. Design decision!

I don't know why we create a genprog-many-bugs directory on line 105, since our
sanity check required its existence several lines above.  Anyway, the CGenProg
scenarios from ManyBugs must all be untarred in /root/genprog-many-bugs, because
that's where they were configured.  That's what happens in the next couple of
lines.

We can delete basically anything to do with templates or templates.c from the
script template and the experiment setup driver. 

The script then compiles the current test.c if necessary.  Again, this is C
specific.

On line 121, the script copies itself to the current directory, so that it can
be saved along with the rest of the results report. 

Line 130 ACTUALLY calls CGenprog.

If the repair run concludes on its own within the time limit, the rest of the
script is run, coping the debug output, cache file, script, possible repairs,
etc into a repair folder and taring it up.  It then copie sit ocver to a machine
hosting results (into a folder whose name is controlled by "BATCH_NAME") and
calls shutdown report.

If the repair run is interrupted by the sleep timeout set on line 70, all that
tarring up of results doesn't happen, and just shutdownreport is called.
shutdownreport saves up debug output and copies it to teh result machine, before
shutting down.  This, by the way, is why some ManyBugs repositories don't have
*-sN-* results associated with them: if they never finish in 12 hours, those
reports aren't created.

If the VM is created with "shutdown behavior" set to "teriminate", shutting down
destroys the virtual machine.  Otherwise, it just sits in your EC2 account with
a "stopped" status, and you can reboot if you want.

In theory, it's possible to run more than one seed in sequence on a given VM
(that's why the calls to repair are run in a for loop).  This can speed things
up when the test cache is saved, but isn't usually worth doing.  At least, we
rarely do it for CGenProg.

## Actually creating those scripts for a set of experiments, creating the VMs, copying over, launching, etc.

The script experiment.py is the main driver.  It takes a few explicit
command-line options, all of which are optional.

The part that's not optional are the directive (or config) files. There are
examples of directive files in this repository: directive.global,
directive.ec2.global, and directive.test.  Any argument that's not an explicit
command line parameter to the script is assumed to be a directive file.  The
idea is that the "global" directive contains settings that don't vary by
experiment, while the test-specific directive contains those that do. This is
not enforced semantically by anything, it's just a convention, as is the naming
scheme of the files.

### Required AWS information

A fair amount of information is required to actually programmatically launch
VMs, including the base AMI, the availability zone, the desired instance type,
and the user's AWS key.  I seem to have made arbitrary decisions about which of
these to hard code and which to read from the directives file (look at
ec2_launch_instances).  I suspect more should be read from the directives files,
with default values provided in the script as applicable. 

### Required non-AWS information

Anything that's in a blank export at the top of
experiments-machine-script-template.sh is required information.

#### how many VMs?

The number of required VMs is computed from the number of multiply-defined
parameters in the directives files.  Notice that directive.test, for example,
has multiple SEEDS= but only one TARBALL.  If there were two TARBALL definitions
(bug 1 and bug 2) there would be #seeds * # tarballs VMs created.

If, for example, you put multiple seeds on one lien (SEEDS="1 2 3"), then those
three seeds are all run (or attempted) on a single VM.

I'm not sure what happens if you try more than one tarball or scenario per
line.  We don't enforce in any way *which* parameters can be multiply-defined,
and just relied on the user (CLG) to not do something weird like specify more
than one AMI.  

Blank lines or lines starting with a pound sign in the directives files are ignored.

### experiment.py

Some of this is sort of commented.  I don't repeat information in this readme
that is contained in function comments, so look at experiment.py while reading
this for more. 


setup(): 

sets up a local workspace (a directory to store intermediate files and log
files.  For example, the output of calls to ec2 CLI, and the instantiated
scripts for each machine, are stored in this workspace).

reads in the directive files and computes the number of required
virtual machines.  It checks that the required arguments in the template are
specified in the directives.

create_scripts() produces lists of arguments that will be used to produce
scripts; basically figures out the singlydefined x multiply defined combinations
taht correspond to the number of VMs, discussed above. 

get_instances() 
Ignoring "premade-instances" for a second, basically just calls launch_instances
for the specified cloud system (again, we can kill all non-ec2 support).  

VMs, when launched, take time to spin up and acquire network addresses.  So,
get_instances repeatedly sleeps a bit, then checks to get the addresses of the
instances we're launching (look at ec2_get_instances).  It tries this some
number of times before giving up.  (D3) 

One of the optional arguments to experiment.py is a list of premade instances to
use.  This is useful mostly when one interrupts experiment.py because of some
observed mistake in setup, *after* launch-instances was called, but *before*
scripts were actually launched on them.  

(to be checked manually, naturally).

prepare_scripts() actually creates the scripts, in the workspace directory.
They are helpfully named N.sh, for N between 1 and the number of instances being
created.  N.sh is experiment-machine-script-template.sh with the missing bits
filled in.  

stage(), for each instance, and each script in N.sh (N \in 1--number instances)
copies N.sh to a unique VM instance. It also copies
"experiment-machine-script-wrapper.sh" and various key files necessary for
communicating with results and host machines over as well.

run() calls experiment-machine-script-wrapper.sh on each machine over ssh for
all instances successfully staged.

Note that all of these steps can fall; see (D3). 


### experiment-machine-script-wrapper.sh

One cannot background commands launched over ssh, and ssh will hang until a
command completes.  So, on each instance, experiment-machine-script.sh is
actually launched using a call to something called
experiment-machine-script-wrapper.sh, which just calls
experiment-machine-script.sh in the background and exits with successful
status.  Yes, this is the best way to do this.

### Root permissions and random systemsy stuff

CGenProg experiments require root; G4J shouldn't.  This is good.  It also means
we probably don't need to modify the AMI to allow sudo without tty.  We may need
to modify the AMI such that sh maps to bash, not dash; I'm not sure if our
current scripts are POSIX compliant, because who cares?

Note the bit in experiment-machine-script above about overcommit-memory.  Ask me
about this if it causes a headache. 