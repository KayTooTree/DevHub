#!/bin/bash
# DEVHUB Bot — manueller Start (fuer systemd siehe devhub-bot.service)
cd "$(dirname "$0")"
python3 bot.py
