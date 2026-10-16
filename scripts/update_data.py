#!/usr/bin/env python3
"""Refresh public sources sequentially, then build the static map. Python 3.10+."""
import argparse,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo-url',default='');a=p.parse_args()
commands=[['geography.py','--download','--build'],['collect_official.py','--output',str(ROOT/'.cache/official'),'--workers','3','--refresh'],['collect_osm.py','--output-dir',str(ROOT/'.cache/osm')],['build_data.py','--repo-url',a.repo_url]]
for command in commands:subprocess.run([sys.executable,str(ROOT/'scripts'/command[0]),*command[1:]],cwd=ROOT,check=True)
