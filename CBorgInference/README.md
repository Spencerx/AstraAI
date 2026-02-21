# Inference using CBorg LBL models

This repository demonstrates how to perform inference using **CBorg LBL models**.

## Steps

1. Go to the [CBorg webpage](https://cborg.lbl.gov/api_examples/) and check the **Key Management** section to create an API key.

2. Add your API key to your environment by editing `~/.bash_profile`:

\```bash
export CBORG_API_KEY=<cborg-key>
\```

Replace `<cborg-key>` with the key obtained in Step 1.

3. Apply the changes:

\```bash
source ~/.bash_profile
\```

4. Run the inference script:

\```bash
python3 cborg_inference.py --cborg-model=<cborg-model> --prompt-file=<user-prompt-file>
\```

   **Arguments:**

   - `--cborg-model`: Name of the CBorg model to use. A list of available models is provided in `cborg_models_list.txt`.  
   - `--prompt-file`: Path to the text file containing the user prompt.

> Example:

\```bash
python3 cborg_inference.py --cborg-model=amazon/claude-sonnet-4-6-high --prompt-file=user_prompt.txt
\```

