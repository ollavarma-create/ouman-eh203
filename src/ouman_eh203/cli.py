"""Core command dispatcher."""
import sys
from .backup import main as backup_main

def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    if args and args[0]=='verify-persistence':
        from .persistence import main as persistence_main
        return persistence_main(args[1:])
    if not args or args[0] in ('-h','--help'):
        print('Additional offline command: verify-persistence (use verify-persistence --help)', flush=True)
    return backup_main(args)
