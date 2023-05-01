# Rosetta Protein-folding workflow

This is a Pegasus workflow for running Rosetta's De novo structure prediction on the OSG. The workflow predicts the 3-dimensional structure of a protein starting with an amino acid sequence, using the [Abinitio Relax](https://new.rosettacommons.org/docs/latest/application_documentation/structure_prediction/abinitio-relax#algorithm) algorithm. This workflow uses ideas from this [tutorial](https://www.rosettacommons.org/demos/latest/tutorials/denovo_structure_prediction/Denovo_structure_prediction).

> Please run the workflow from your [OSG Connect](https://www.osgconnect.net) account. Anyone with a U.S. research affiliation can get access.


# Configure Input files
You will need to have a license to download Rosetta. See the [Rosetta documentation](https://www.rosettacommons.org/demos/latest/tutorials/install_build/install_build) for details on how to obtain the license. Once you have the license, you can download the Rosetta software suite from https://www.rosettacommons.org/software/license-and-download.

Untar the downloaded file by running this command in your terminal:

```tar -xvzf rosetta[releasenumber].tar.gz```

## Binaries

The ab initio executable can be found in ```rosetta*/main/source/bin```. Navigate to this directory and copy the AbinitioRelax file to the ```bin``` directory of the rosetta_workflow. Make sure the file name in the last line of proteinfold.sh matches the one you copied. 

## Database
The Pegasus workflow takes as input the database as a tarball file. Create the tar file of the database folder found in ```rosetta*/main``` and place it in the ```database``` directory of the workflow. 

```cd [path to rosetta*]/main/ && tar -czf [path to rosetta workflow]/database/database.tar.gz database```

## Data inputs
A job in the rosetta workflow requires the following input files for an amino acid sequence:

* Fasta file - Example: 1elwA.fasta

* Fragments files - Example: aa1elwA03_05.200_v1_3 and aa1elwA09_05.200_v1_3

* PDB file. Example - 1elw.pdb

* Psipred secondary structure prediction psipred_ss2 file - Example: 1elwA.psipred_ss2

> **Note**: Rename the input files to have the same base name. 
>               
> Example: data-1.fasta, data-1.pdb, data-1.psipred_ss2, data-1-09_05.200_v1_3, data-1-03_05.200_v1_3 and the folder containing these input files as data-1.

Run the command on the folder ```data-<i>``` containing the above input files for a sequence

```tar -cf data-<i>.tar.gz data-<i> ```

A proteinfold job is created for each file in ```inputs/```. The workflow structure is a set of independent tasks executing ```bin/proteinfold.sh``` that takes the data tar file and database tar as input and produces a silent file as output.

Note that in the Transformation catalog section of the workflow, the clustering feature is enabled. This tells Pegasus to cluster multiple jobs together.

        proteinfold = Transformation(
                name="proteinfold",
                site="local",
                pfn=TOP_DIR / "bin/proteinfold.sh",
                is_stageable="True",
                arch=Arch.X86_64).add_pegasus_profile(clusters_size=10)

To disable clustering, set ```clusters_size``` to 1. Experiment with different values for ```clusters_size``` and observe how it affects the time required for the jobs to finish.

# Run the workflow

Submit the workflow by executing ```proteinfolding.py```.

        $ ./proteinfolding.py

You can use ```pegasus-status``` to check the status of the workflow and ```pegasus-statistics``` to display statistics once the workflow completes. 

        $ pegasus-status [wfdir]
        $ pegasus-statistics [wfdir]

Outputs will be automatically staged to ```/home/$USER/workflows/output```



