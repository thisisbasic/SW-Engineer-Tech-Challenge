#!/usr/bin/env bash

pip install -r rest_api/requirements.txt
(cd rest_api && uvicorn main:app --reload)