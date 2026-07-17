#!/bin/bash
# DEVHUB Agent — manueller Start (fuer systemd siehe devhub-agent.service)
cd "$(dirname "$0")"
python3 agent.py
