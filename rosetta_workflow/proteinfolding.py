#!/usr/bin/env python3
import logging
import glob
import os
import getpass
from pathlib import Path

from Pegasus.api import *

logging.basicConfig(level=logging.INFO)

# --- Working Directory Setup --------------------------------------------------
# A good working directory for workflow runs and output files
WORK_DIR = Path.home() / "workflows"
WORK_DIR.mkdir(exist_ok=True)

TOP_DIR = Path(__file__).resolve().parent

# --- Properties ---------------------------------------------------------------
props = Properties()
props["pegasus.data.configuration"] = "nonsharedfs"  

# Provide a full kickstart record, including the environment, even for successful jobs
props["pegasus.gridstart.arguments"] = "-f"

#Limit the number of idle jobs for large workflows
props["dagman.maxidle"] = "1600"

# Help Pegasus developers by sharing performance data (optional)
props["pegasus.monitord.encoding"] = "json"
props["pegasus.catalog.workflow.amqp.url"] = "amqp://friend:donatedata@msgs.pegasus.isi.edu:5672/prod/workflows"

# write properties file to ./pegasus.properties
props.write()

# --- Sites --------------------------------------------------------------------
sc = SiteCatalog()

# local site (submit machine)
local_site = Site(name="local", arch=Arch.X86_64)

local_shared_scratch = Directory(directory_type=Directory.SHARED_SCRATCH, path=WORK_DIR / "scratch")
local_shared_scratch.add_file_servers(FileServer(url="file://" + str(WORK_DIR / "scratch"), operation_type=Operation.ALL))
local_site.add_directories(local_shared_scratch)

local_storage = Directory(directory_type=Directory.LOCAL_STORAGE, path=WORK_DIR / "output")
local_storage.add_file_servers(FileServer(url="file://" + str(WORK_DIR / "output"), operation_type=Operation.ALL))
local_site.add_directories(local_storage)

local_site.add_env(PATH=os.environ["PATH"])
sc.add_sites(local_site)

# stash site (staging site, where intermediate data will be stored)
stash_site = Site(name="stash", arch=Arch.X86_64, os_type=OS.LINUX)
stash_staging_path = "/public/{USER}/staging".format(USER=getpass.getuser())
stash_shared_scratch = Directory(directory_type=Directory.SHARED_SCRATCH, path=stash_staging_path)
stash_shared_scratch.add_file_servers(
    FileServer(
        url="stash:///osgconnect{STASH_STAGING_PATH}".format(STASH_STAGING_PATH=stash_staging_path), 
        operation_type=Operation.ALL)
)
stash_site.add_directories(stash_shared_scratch)
sc.add_sites(stash_site)

# condorpool (execution site)
condorpool_site = Site(name="condorpool", arch=Arch.X86_64, os_type=OS.LINUX)
condorpool_site.add_pegasus_profile(style="condor")
condorpool_site.add_condor_profile(
    universe="vanilla",
    requirements='HAS_SINGULARITY == True && !regexp(GLIDEIN_Site, "SU-ITS|SDSC-PRP|Purdue Anvil")',
    request_cpus=5,
    request_memory="3 GB",
    request_disk="10000000",
)
condorpool_site.add_profiles(
    Namespace.CONDOR, 
    key="+SingularityImage", 
    value='"/cvmfs/singularity.opensciencegrid.org/opensciencegrid/osgvo-el7:latest"'
)

sc.add_sites(condorpool_site)

# write SiteCatalog to ./sites.yml
sc.write()

# --- Transformations ----------------------------------------------------------
proteinfold = Transformation(
	name="proteinfold",
	site="local",
	pfn=TOP_DIR / "bin/proteinfold.sh",
	is_stageable="True",
	arch=Arch.X86_64).add_pegasus_profile(clusters_size=1)

tc = TransformationCatalog()
tc.add_transformations(proteinfold)

# write TransformationCatalog to ./transformations.yml
tc.write()

# --- Replicas -----------------------------------------------------------------
exec_file = [File(f.name) for f in (TOP_DIR / "bin").iterdir() if f.name.startswith("AbinitioRelax")]

input_files = [File(f.name) for f in (TOP_DIR / "inputs").iterdir()]

db_files = [File(f.name) for f in (TOP_DIR / "database").iterdir()]

rc = ReplicaCatalog()

for f in input_files:
	rc.add_replica(site="local", lfn=f, pfn=TOP_DIR / "inputs" / f.lfn)	

for f in exec_file:
    rc.add_replica(site="local", lfn=f, pfn=TOP_DIR / "bin" / f.lfn)

for f in db_files:
    rc.add_replica(site="local", lfn=f, pfn=TOP_DIR / "database" / f.lfn)
	
# write ReplicaCatalog to replicas.yml
rc.write()

# --- Workflow -----------------------------------------------------------------
wf = Workflow(name="protein-folding-workflow")

for f in input_files:

	filename = f.lfn.replace(".tar.gz","")
	out_file = File(filename + "_silent.out")

	proteinfold_job = Job(proteinfold).add_args(filename, "-database ./database","-in:file:fasta",f"./{filename}.fasta",
			"-in:file:frag3",f"./{filename}-03_05.200_v1_3",
			"-in:file:frag9",f"./{filename}-09_05.200_v1_3","-in:file:native",f"./{filename}.pdb",
			"-abinitio:relax","-nstruct","1",
			"-out:file:silent", out_file,
			"-use_filters","true","-psipred_ss2",f"./{filename}.psipred_ss2",
			"-abinitio::increase_cycles","10",
			"-abinitio::rg_reweight","0.5","-abinitio::rg_reweight","0.5",
			"-abinitio::rsd_wt_helix","0.5","-abinitio::rsd_wt_loop","0.5","-relax::fast")\
			.add_inputs(exec_file[0],db_files[0],f).add_outputs(out_file)
	wf.add_jobs(proteinfold_job)

# plan and run the workflow
wf.plan(
    dir=WORK_DIR / "runs",
    sites=["condorpool"],
    staging_sites={"condorpool":"stash"},
    output_sites=["local"],
    cluster=["horizontal"],
    submit=True
)
