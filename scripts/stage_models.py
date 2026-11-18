"""Copy only hash-verified model artifacts into the AWS image build context."""
import argparse
from pathlib import Path
import shutil
from ml.registry import manifest

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',default='artifacts/models');parser.add_argument('--target',default='cloud-models')
    args=parser.parse_args()
    for name in ['lightgbm','tgn']:
        source=Path(args.source)/name;m=manifest(source,name)
        target=Path(args.target)/name;target.mkdir(parents=True,exist_ok=True)
        for filename in [*m['checkpoints'],'manifest.json']:shutil.copyfile(source/filename,target/filename)
        manifest(target,name)
        print(name,m['model_version'])
if __name__=='__main__':main()
