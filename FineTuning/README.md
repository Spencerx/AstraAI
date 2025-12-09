# Fine-Tuning Mistral 7B on Perlmutter GPUs

## What is needed?

1. [Instruction-response pairs as in the InstructionResponsePairs folder](https://github.com/AIModCon/modcon-hpc/blob/main/FineTuning/InstructionResponsePairs/amrex_inst_resp_pairs.txt)
2. Convert the instruction response pairs to `.jsonl` format by running the python script
```
cd InstructionResponsePairs
python3 ConvertToJSONL.py
```
This will produce the instruction response pairs in `.jsonl` format that is needed for fine tuning.

3. Enter the Mistral environment created using the steps mentioned in the [README section](https://github.com/AIModCon/modcon-hpc/tree/main?tab=readme-ov-file#mistral-environment-setup-on-linux) 
```
source <path-to-mistral-env>/bin/activate
```
4. Get a GPU node and run the python script for fine tuning   
`python3 FineTuning.py`

![Example of fine tuning of mistral 7b model on Perlmutter GPUs for AMReX](../Images/FineTuning.gif)

This animation demonstrates the fine-tuning workflow of the Mistral-7B model on NERSC Perlmutter GPUs for use within AMReX-based applications.

