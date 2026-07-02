#!/usr/bin/env bash
set -e
python ./runtime_patch.py
python ./extra_knowledge_patch.py
python ./identity_answer_patch.py
python ./bot.py
