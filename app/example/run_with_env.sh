#!/bin/bash

export OPENAI_API_KEY=$(grep OPENAI_API_KEY config.toml | cut -d'"' -f2)
export OPENAI_API_BASE=$(grep OPENAI_API_BASE config.toml | cut -d'"' -f2)

source ../env/bin/activate
python run_demo.py
