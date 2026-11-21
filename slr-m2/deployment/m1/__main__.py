import argparse
import sys
from pathlib import Path
from .common import ROOT, DEFAULT_BUNDLE, check_bundle, read, write

def main():
    parser = argparse.ArgumentParser(description='Local 07b recorded-video inspector')
    parser.add_argument('--bundle',type=Path,default=DEFAULT_BUNDLE)
    sub = parser.add_subparsers(dest='command',required=True)
    sub.add_parser('preflight')
    evaluation = sub.add_parser('evaluate')
    evaluation.add_argument('run',type=Path)
    evaluation.add_argument('--revisions',nargs='+',required=True)
    replay = sub.add_parser('replay')
    replay.add_argument('video',type=Path)
    replay.add_argument('--output',type=Path,default=ROOT/'outputs/m1')
    replay.add_argument('--config',type=Path)
    replay.add_argument('--boundaries-only',action='store_true')
    serve = sub.add_parser('serve')
    serve.add_argument('run',type=Path)
    serve.add_argument('--port',type=int,default=8765)
    args = parser.parse_args()
    try:
        if args.command == 'preflight':
            identity=check_bundle(args.bundle)
            identity.pop('labels')
            print(identity)
        elif args.command == 'replay':
            from .replay import replay as execute
            from .segmenter import Config
            config=Config(**read(args.config)) if args.config else Config()
            print(execute(args.video,args.bundle,args.output,config,args.boundaries_only))
        elif args.command == 'evaluate':
            from .evaluation import evaluate
            print(evaluate(args.run,args.revisions))
        elif args.command == 'serve':
            import uvicorn
            from .server import app_for
            uvicorn.run(app_for(args.run,args.bundle),host='127.0.0.1',port=args.port)
    except (ValueError, FileNotFoundError) as error:
        parser.exit(2,f'{error}\n')

if __name__ == '__main__':
    main()
