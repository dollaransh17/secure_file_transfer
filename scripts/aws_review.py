"""Local AWS deployment review. No AWS requests, authentication or provisioning."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def review(parameters=None,mode='minimal'):
    if mode not in {'minimal','full'}:
        raise ValueError('Choose minimal or full cloud review')
    filename='minimal-storage.json' if mode=='minimal' else 'template.json'
    template=json.loads((ROOT/'infrastructure/aws'/filename).read_text())
    resources=template['Resources'];counts=Counter(r['Type'] for r in resources.values())
    supplied={}
    if parameters:
        data=json.loads(Path(parameters).read_text())
        supplied={entry['ParameterKey']:entry['ParameterValue'] for entry in data}
    missing=[];invalid=[]
    for name,spec in template['Parameters'].items():
        value=supplied.get(name,spec.get('Default'))
        if value is None or isinstance(value,str) and value.startswith('REPLACE_'):
            missing.append(name);continue
        if 'AllowedPattern' in spec and re.fullmatch(spec['AllowedPattern'],str(value)) is None:invalid.append(name)
    tasks=[]
    for name,resource in resources.items():
        if resource['Type']!='AWS::ECS::Service':continue
        task_name=resource['Properties']['TaskDefinition']['Ref']
        task=resources[task_name]['Properties'];count=resource['Properties']['DesiredCount']
        tasks.append({'service':name,'replicas':count,'vcpu_per_task':int(task['Cpu'])/1024,'memory_gib_per_task':int(task['Memory'])/1024})
    return {'resources_to_review':dict(sorted(counts.items())),'ecs_tasks':tasks,
        'total_fargate_vcpu':sum(t['replicas']*t['vcpu_per_task'] for t in tasks),
        'total_fargate_memory_gib':sum(t['replicas']*t['memory_gib_per_task'] for t in tasks),
        'missing_parameters':missing,'invalid_parameters':invalid,
        'mode':mode,
        'billable_components':(['S3/all object versions and requests','KMS requests using AWS-managed aws/s3 key','SQS notifications, receives including empty polling, deletes and DLQ operations','Applicable data transfer'] if mode=='minimal' else ['Fargate compute','NAT gateway and traffic','Application Load Balancer','RDS','ElastiCache','two KMS keys','S3/version storage and requests','SQS','CloudWatch logs/metrics','ECR image storage']),
        'pricing':'No price estimate made; review current pricing in the chosen region before approval.',
        'aws_actions_performed':False,'deployment_approved':False,
        'scope':('Hybrid research: cloud storage and event notifications only; application/database/scanning/ML remain local. Not public cloud hosting; no guaranteed $1 cap.' if mode=='minimal' else 'Research configuration with single NAT/database/scanner; no high-availability production claim.')}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parameters');p.add_argument('--mode',choices=['full','minimal'],default='minimal');p.add_argument('--output',default='artifacts/aws-review.json');a=p.parse_args()
    report=review(a.parameters,a.mode);out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
