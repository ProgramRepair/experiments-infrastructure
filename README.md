# experiments-infrastructure
Scripts and other support for launching and managing large-scale repair
experiments on a cloud infrastructure (usually EC2). 

## disclaimer

The existing set of scripts is a huge kludge that was never intended to survive
as long as it has.  I look forward to generalizing it and improving its design,
usability, and maintainability.

## somewhat relevant history

The current scripts in this repository are taken from a private svn repository
(hosted at UVA).  These scripts have been used to launch and manage repair
experiments across many virtual machines in one of several cloud frameworks.
The most robust and best-tested and most widely used of these modes is EC2,
though the protocol was roughly the same for all of them.

## Design decisions

(D1) One or many? We can either generalize the approach to work across many different types of
repair experiment launches (GenProg4Java vs GenProg4C) or instantiate two sets
of scripts, one for Java and one for C.  I propose something close to the former
approach, with customization; more suggestions below.  CLG anticipates we can
remove (or simply not re-implement) support for the other cloud types moving
forward, regardless of which way we go.

## High-level Workflow

(I use CGenprog to refer to the GenProg4C code and G4J for GenProg4Java
throughout this explanation.)

Here's the general idea: the user specifies the scenario name, configuration
file and any arguments to pass to CGenProg, and each random seed on which she
wants it to be run.  The script launches one VM per seed on which genprog will
be run; and then creates a script to conduct the actual run, copies it over to a
VM, and launches it remotely. More on that in a minute.

## A single experiment script 

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
scenarios differently, by updating defects4j (which should be checked out on the
VM already) to a specified (or most current? Design decision! Either way, we
need to write out to the log which version of Defects4J (and genprog4j?) was
used for a particular experimental run) revision and calling a setup script to
setup the particular scenario we want to try to repair (which will need to be
user specified, so added to the exports at the top, if we follow the current
paradigm), presumbly from the genprog4java repository (which will need to be
updated, either to a specified SHA or most recent, as with defects4j).  

If defects4j or g4j are either not present on the machine or not available to be
copied over, this should be considered a failure.

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

## Actually creating those scripts for a set of experiments


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
ec2_launch_instances).




### Required non-AWS information

