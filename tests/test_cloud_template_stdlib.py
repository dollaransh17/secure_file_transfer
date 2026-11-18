import json
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
class CloudTemplate(unittest.TestCase):
    def setUp(self):self.t=json.loads((ROOT/'infrastructure/aws/template.json').read_text());self.r=self.t['Resources']
    def test_all_logical_references_resolve(self):
        names=set(self.r)|set(self.t['Parameters'])
        def walk(node):
            if isinstance(node,dict):
                if 'Ref' in node:self.assertTrue(node['Ref'] in names or node['Ref'].startswith('AWS::'),node['Ref'])
                if 'Fn::GetAtt' in node:self.assertIn(node['Fn::GetAtt'][0],self.r)
                if 'Fn::Sub' in node and isinstance(node['Fn::Sub'],str):
                    for name in re.findall(r'\$\{([^}]+)\}',node['Fn::Sub']):self.assertTrue(name.split('.')[0] in names or name.startswith('AWS::'),name)
                for value in node.values():walk(value)
            elif isinstance(node,list):
                for value in node:walk(value)
        walk(self.t)
    def test_private_versioned_kms_storage(self):
        s=self.r['Files']['Properties'];self.assertEqual(s['VersioningConfiguration']['Status'],'Enabled')
        self.assertTrue(all(s['PublicAccessBlockConfiguration'].values()))
        self.assertEqual(s['BucketEncryption']['ServerSideEncryptionConfiguration'][0]['ServerSideEncryptionByDefault']['SSEAlgorithm'],'aws:kms')
    def test_database_not_public_and_password_not_embedded(self):
        s=self.r['Database']['Properties'];self.assertFalse(s['PubliclyAccessible']);self.assertTrue(s['StorageEncrypted']);self.assertTrue(s['ManageMasterUserPassword']);self.assertNotIn('MasterUserPassword',s)
    def test_secret_key_is_never_parameter(self):
        self.assertNotIn('AnthropicApiKey',self.t['Parameters'])
        task=self.r['ApiTask']['Properties']['ContainerDefinitions'][0]
        self.assertNotIn('ANTHROPIC_API_KEY',{e['Name'] for e in task['Environment']})
        self.assertTrue(task['Secrets'])
    def test_tasks_are_private(self):
        for name in ['Api','Worker','Clamav','Web']:
            net=self.r[name+'Service']['Properties']['NetworkConfiguration']['AwsvpcConfiguration'];self.assertEqual(net['AssignPublicIp'],'DISABLED')
    def test_tls13_policy(self):self.assertEqual(self.r['Https']['Properties']['SslPolicy'],'ELBSecurityPolicy-TLS13-1-3-2021-06')
    def test_queue_is_encrypted_and_dead_lettered(self):
        queue=self.r['StorageEvents']['Properties'];self.assertIn('KmsMasterKeyId',queue);self.assertEqual(queue['RedrivePolicy']['maxReceiveCount'],5)
    def test_no_secret_literals_in_template(self):
        text=json.dumps(self.t)
        self.assertNotIn('sk-ant-',text);self.assertNotRegex(text, r'local-development-[a-z]+')
    def test_direct_validation_size(self):self.assertLess((ROOT/'infrastructure/aws/template.json').stat().st_size,51200)

    def test_resource_dependency_graph_is_acyclic(self):
        def references(node):
            found=set()
            if isinstance(node,dict):
                if node.get('Ref') in self.r:found.add(node['Ref'])
                if 'Fn::GetAtt' in node:found.add(node['Fn::GetAtt'][0])
                if isinstance(node.get('Fn::Sub'),str):
                    found.update(n.split('.')[0] for n in re.findall(r'\$\{([^}]+)\}',node['Fn::Sub']) if n.split('.')[0] in self.r)
                for value in node.values():found|=references(value)
            elif isinstance(node,list):
                for value in node:found|=references(value)
            return found
        graph={}
        for name,resource in self.r.items():
            explicit=resource.get('DependsOn',[])
            graph[name]=references(resource)|set([explicit] if isinstance(explicit,str) else explicit)
        active=set();visited=set()
        def visit(name):
            self.assertNotIn(name,active,'CloudFormation resource dependency cycle')
            if name in visited:return
            active.add(name)
            for dependency in graph[name]:visit(dependency)
            active.remove(name);visited.add(name)
        for name in graph:visit(name)
