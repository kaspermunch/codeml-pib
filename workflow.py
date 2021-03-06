
import os, glob, re
from gwf import Workflow

# function for easy manipulation of file paths
def modpath(p, parent=None, base=None, suffix=None):     
    par, name = os.path.split(p)
    name_no_suffix, suf = os.path.splitext(name)
    if type(suffix) is str:
        suf = suffix
    if parent is not None:
        par = parent
    if base is not None:
        name_no_suffix = base

    new_path = os.path.join(par, name_no_suffix + suf)
    if type(suffix) is tuple:
        assert len(suffix) == 2
        new_path, nsubs = re.subn(r'{}$'.format(suffix[0]), suffix[1], new_path)
        assert nsubs == 1, nsubs
    return new_path

# the gwf object controlling the workflow
gwf = Workflow(defaults={'account': 'simons'})

###########################################################################
# input data
###########################################################################

# the subset of genes you are analyzing
import pandas as pd
df = pd.read_hdf('~/simons/faststorage/people/kmt/results/candidate_genes.hdf')
included_genes = df.name.tolist()
#included_genes = ['DYNLT3']#, 'CFAP47', 'LAS1L', 'ZCCHC13', 'IL13RA2', 'HTR2C', 'ACTRT1', 'MAOA']

# all the phylib files you have generated
all_phylip_files = glob.glob('steps/cds_data/*.phylib')

# make a list of only the phylib files for the genes you are analyzing
phylib_files = []
for phylib_file in all_phylip_files:
     gene_name = modpath(phylib_file, suffix='', parent='')
     if gene_name in included_genes:
          phylib_files.append(phylib_file)

# list of all the output files generated by codeml
codeml_output_files = []

###########################################################################
# codeml analysis
###########################################################################

# loop over the phylib files
for phylib_file in phylib_files:

     # get the gene name from the file name
     gene_name = modpath(phylib_file, suffix='', parent='')

     # the name of the tree file is the same as the phylib file but with a .nw suffix
     tree_file = modpath(phylib_file, suffix='.nw')

     # the output dir for codeml output files
     codeml_output_dir = f'steps/codeml/{gene_name}'
     # codeml_output_dir = f'./steps/codeml/{gene_name}'

     # make the dir if it does not exist already
     if not os.path.exists(codeml_output_dir):
          os.makedirs(codeml_output_dir)

     # create the name of the codeml output file 
     # same as the the phylib file but we give it a .txt suffix and make its dir the codeml outpur dir
     codeml_output_file = modpath(phylib_file, suffix='.txt', parent=codeml_output_dir)

     # almost the same for the control file
     codeml_control_file = modpath(phylib_file, suffix='.ctl', parent=codeml_output_dir)

     # add the codeml output file to the list of all output files
     codeml_output_files.append(codeml_output_file)

     # make a gwf target (cluster job) to run a codeml analysis
     tag = gene_name.replace('-', '_')
     gwf.target(name=f'codeml_{tag}',
               inputs=[phylib_file, tree_file], 
               outputs=[codeml_output_file, codeml_control_file], 
               cores=1,
               walltime='02:00:00', 
               memory='8g') << f"""

     python scripts/codeml.py {phylib_file} {tree_file} {codeml_output_file} {os.path.basename(codeml_control_file)} {codeml_output_dir}
     sleep 5
     """

###########################################################################
# parse output from codeml analyses
###########################################################################

# the output dir for the summary files produced by parsing codeml output files
summary_output_dir = 'steps/summary'
# summary_output_dir = './steps/summary'

# make the dir if it does not exist already
if not os.path.exists(summary_output_dir):
     os.makedirs(summary_output_dir)

# loop over all the codeml output files
for codeml_output_file in codeml_output_files:

     # get the gene name from the file name
     gene_name = modpath(codeml_output_file, suffix='', parent='')

     # create the name of the summary output file 
     # same as the the codeml output file but we make its dir the summary outpur dir
     summary_file = modpath(codeml_output_file, suffix='.txt', parent=summary_output_dir)

     # make a gwf target (cluster job) to run a the parse script
     tag = gene_name.replace('-', '_')
     gwf.target(name=f'parse_{tag}',
               inputs=[codeml_output_file], 
               outputs=[summary_file], 
               cores=1,
               walltime='00:10:00', 
               memory='8g') << f"""

     python scripts/parse_codeml.py {codeml_output_file} {summary_file}

     """
