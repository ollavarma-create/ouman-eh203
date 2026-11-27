"""Offline metadata presentation commands."""
import argparse
import json
from pathlib import Path
from .metadata import get_metadata
from .registry import FIELDS
from .defaults import compare_defaults

def main(command, argv=None):
    parser=argparse.ArgumentParser(prog='ouman-eh203 '+command)
    parser.add_argument('--output',type=Path)
    if command=='compare-defaults':
        parser.add_argument('--source',type=Path,required=True)
        parser.add_argument('--confirm-factory-reset',action='store_true')
    else:
        parser.add_argument('--lang',choices=('fi','en'),default='fi')
        parser.add_argument('--key',choices=[f[0] for f in FIELDS])
    args=parser.parse_args(argv)
    try:
        if command=='compare-defaults':
            report=compare_defaults(json.loads(args.source.read_text(encoding='utf-8')),
                                    factory_reset_confirmed=args.confirm_factory_reset)
        else:
            rows={}
            for key,pid,offset,width,signed,factor,unit in FIELDS:
                if args.key and key!=args.key:
                    continue
                meta=get_metadata(key)
                meta['display_label']=meta['label'][args.lang] or key
                meta['protocol']=dict(id=pid,data_offset=offset,width=width,
                                      signed=signed,factor=factor,unit=unit)
                rows[key]=meta
            report=dict(schema='ouman.eh203.metadata.v1',language=args.lang,
                        read_only=True,fields=rows)
        payload=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        if args.output:
            with args.output.open('x',encoding='utf-8') as f:
                f.write(payload)
        else:
            print(payload,end='')
        return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        parser.exit(1,f'Error: {exc}\n')
