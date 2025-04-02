# PRJ-Mesa-Geo

## Basic Setup

This model was designed on Ubuntu, and thus may not work on other operating systems.

Set up an environment using **conda**:
`conda env create --file environment.yml`

Activate the environment with:
`conda activate prj_mesa_geo`

## LLM Setup

The model was implemented to work with [LM Studio](https://lmstudio.ai/), but can be easily adjusted to work with different software.
This can be done by changing the IP address defined in 'client' at the top of `llm.py`.

The LLM expected is [Meta-Llama-3-8B-Instruct-GGUF](https://huggingface.co/SanctumAI/Meta-Llama-3-8B-Instruct-GGUF).

Run the LLM using the local server of LM Studio under the 'Developer' tab.

## Running The Model

Run the visualisation by opening the console in this top-level directory and running:
`solara run app.py`

To run the model without the visualisation, run the script `headless_run.py`.

The source code comes with the westerham scenario already, but new scenarios can be created using functions in `utils/create_scenario.py`.

Analysis of model results can be done using functions in `utils/analysis.py`.
