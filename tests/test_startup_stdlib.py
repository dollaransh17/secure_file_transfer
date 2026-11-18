"""Startup orchestration regression checks. No Docker daemon is used."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Startup(unittest.TestCase):
    @unittest.skipUnless(shutil.which('docker'), 'Docker CLI required to normalize Compose configuration')
    def test_one_builder_for_shared_api_tag(self):
        result = subprocess.run(['docker','compose','--env-file','config/local.example','config','--format','json'],
                                cwd=ROOT,capture_output=True,text=True,check=True)
        services = json.loads(result.stdout)['services']
        users = {name: value for name,value in services.items() if value.get('image')=='prooflane-api:local'}
        self.assertEqual(set(users), {'api','migrate','storage-init','worker','worker-2'})
        self.assertEqual([name for name,value in users.items() if 'build' in value], ['api'])
        self.assertTrue(all(value.get('pull_policy')=='never' for value in users.values()))

    def run_script(self, build_exit):
        with tempfile.TemporaryDirectory() as directory:
            workspace=Path(directory)
            (workspace/'scripts').mkdir();(workspace/'bin').mkdir()
            (workspace/'.env').write_text('ENVIRONMENT=development\n')
            script=workspace/'scripts/start-local.sh'
            shutil.copyfile(ROOT/'scripts/start-local.sh',script)
            docker=workspace/'bin/docker'
            docker.write_text('''#!/bin/sh
printf '%s\\n' "$*" >> "$PROOFLANE_TEST_TRACE"
case "$*" in
  'compose build api minio web') exit "$PROOFLANE_TEST_BUILD_EXIT" ;;
esac
exit 0
''')
            docker.chmod(0o755)
            environment=os.environ.copy()
            environment['PATH']=str(workspace/'bin')+os.pathsep+environment['PATH']
            environment['PROOFLANE_TEST_TRACE']=str(workspace/'trace')
            environment['PROOFLANE_TEST_BUILD_EXIT']=str(build_exit)
            result=subprocess.run(['sh',str(script)],env=environment,capture_output=True,text=True,timeout=10)
            commands=(workspace/'trace').read_text().splitlines()
            return result,commands

    def test_build_completes_before_service_start(self):
        result,commands=self.run_script(0)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(commands.count('compose build api minio web'),1)
        self.assertLess(commands.index('compose build api minio web'),commands.index('compose up --no-build -d --wait --wait-timeout 600'))
        self.assertIn('Prooflane is ready:',result.stdout)

    def test_failed_build_does_not_start_services_or_report_ready(self):
        result,commands=self.run_script(42)
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(any(command.startswith('compose up ') for command in commands))
        self.assertNotIn('Prooflane is ready:',result.stdout)
        self.assertIn('image build failed',result.stderr)

if __name__=='__main__':unittest.main()
