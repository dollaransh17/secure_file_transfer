"""Validate configured account/model availability without printing credentials."""
import argparse
import json
from prooflane.config import settings

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe',action='store_true',help='Make one short billable generation with no application evidence')
    args=parser.parse_args()
    s=settings()
    if not s.anthropic_api_key or not s.anthropic_model:
        raise SystemExit('Set ANTHROPIC_API_KEY and ANTHROPIC_MODEL, then recreate the API container')
    from anthropic import Anthropic
    client=Anthropic(api_key=s.anthropic_api_key,timeout=20,max_retries=1)
    try:
        model=client.models.retrieve(s.anthropic_model)
        result={'available':True,'requested_model':s.anthropic_model,'resolved_model':model.id}
        if args.probe:
            response=client.messages.create(model=s.anthropic_model,max_tokens=16,
                messages=[{'role':'user','content':'Reply with OK.'}])
            result['usage']={'input_tokens':response.usage.input_tokens,'output_tokens':response.usage.output_tokens}
        print(json.dumps(result,indent=2))
    except Exception as error:
        print(json.dumps({'available':False,'model':s.anthropic_model,'error_type':type(error).__name__}))
        raise SystemExit(1)

if __name__=='__main__':main()
