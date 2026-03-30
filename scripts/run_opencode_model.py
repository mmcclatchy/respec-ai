#!/usr/bin/env python3

import sys
from argparse import ArgumentParser

from src.cli.commands.opencode_model import add_arguments, run


parser = ArgumentParser(description='Run opencode-models directly for debugging')
add_arguments(parser)
sys.exit(run(parser.parse_args()))
