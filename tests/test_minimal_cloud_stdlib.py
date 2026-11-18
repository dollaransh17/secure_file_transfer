"""Minimal cloud boundaries. These inspect source, not deployed AWS resources."""
import json
from pathlib import Path
import re
import unittest

from infrastructure.aws.build_minimal_template import generate
from scripts.aws_review import review

ROOT = Path(__file__).resolve().parents[1]


class MinimalCloud(unittest.TestCase):
    def setUp(self):
        self.template = generate()
        self.resources = self.template['Resources']

    def test_generated_artifact_matches_source(self):
        self.assertEqual(self.template, json.loads((ROOT/'infrastructure/aws/minimal-storage.json').read_text()))

    def test_template_references_resolve(self):
        names = set(self.resources) | set(self.template['Parameters'])

        def walk(node):
            if isinstance(node, dict):
                if 'Ref' in node:
                    self.assertTrue(node['Ref'] in names or node['Ref'].startswith('AWS::'))
                if 'Fn::GetAtt' in node:
                    self.assertIn(node['Fn::GetAtt'][0], self.resources)
                if isinstance(node.get('Fn::Sub'), str):
                    for name in re.findall(r'\$\{([^}]+)\}', node['Fn::Sub']):
                        self.assertTrue(name.split('.')[0] in names or name.startswith('AWS::'), name)
                elif isinstance(node.get('Fn::Sub'), list):
                    pattern, variables = node['Fn::Sub']
                    for name in re.findall(r'\$\{([^}]+)\}', pattern):
                        self.assertTrue(name in variables or name.split('.')[0] in names or name.startswith('AWS::'), name)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(self.template)

    def test_only_storage_queues_and_unattached_access_policies(self):
        self.assertEqual(sorted(r['Type'] for r in self.resources.values()), sorted([
            'AWS::S3::Bucket', 'AWS::S3::BucketPolicy',
            'AWS::SQS::Queue', 'AWS::SQS::Queue', 'AWS::SQS::QueuePolicy',
            'AWS::IAM::ManagedPolicy', 'AWS::IAM::ManagedPolicy']))
        for name in ['ApiStoragePolicy', 'WorkerStoragePolicy']:
            props = self.resources[name]['Properties']
            self.assertTrue({'Users', 'Groups', 'Roles'}.isdisjoint(props))

    def test_private_versioned_storage_survives_stack_deletion(self):
        bucket = self.resources['Files']
        self.assertEqual(bucket['DeletionPolicy'], 'Retain')
        self.assertEqual(bucket['UpdateReplacePolicy'], 'Retain')
        props = bucket['Properties']
        self.assertEqual(props['VersioningConfiguration']['Status'], 'Enabled')
        self.assertTrue(all(props['PublicAccessBlockConfiguration'].values()))
        self.assertEqual(props['OwnershipControls']['Rules'], [{'ObjectOwnership': 'BucketOwnerEnforced'}])

    def test_kms_encryption_without_customer_key_resource(self):
        encryption = self.resources['Files']['Properties']['BucketEncryption']['ServerSideEncryptionConfiguration'][0]
        self.assertTrue(encryption['BucketKeyEnabled'])
        self.assertEqual(encryption['ServerSideEncryptionByDefault'], {'SSEAlgorithm': 'aws:kms'})
        self.assertEqual(self.template['Outputs']['EncryptionKeyId']['Value'], 'alias/aws/s3')

    def test_tls_and_explicit_kms_are_required(self):
        statements = self.resources['FilesPolicy']['Properties']['PolicyDocument']['Statement']
        tls, kms = statements
        self.assertTrue(all(s['Effect'] == 'Deny' for s in statements))
        self.assertEqual(tls['Condition'], {'Bool': {'aws:SecureTransport': 'false'}})
        self.assertEqual(kms['Action'], 's3:PutObject')
        self.assertEqual(kms['Condition'], {'StringNotEquals': {'s3:x-amz-server-side-encryption': 'aws:kms'}})

    def test_api_and_worker_cannot_delete_or_administer_storage(self):
        for name in ['ApiStoragePolicy', 'WorkerStoragePolicy']:
            statements = self.resources[name]['Properties']['PolicyDocument']['Statement']
            actions = {a for statement in statements for a in statement['Action']}
            expected = {'s3:GetBucketVersioning', 's3:GetObjectVersion', 'kms:Decrypt'}
            if name == 'ApiStoragePolicy':
                expected |= {'s3:PutObject', 'kms:GenerateDataKey'}
            else:
                expected |= {'sqs:ReceiveMessage', 'sqs:DeleteMessage', 'sqs:ChangeMessageVisibility', 'sqs:GetQueueAttributes'}
            self.assertEqual(actions, expected)
            kms = next(s['Condition'] for s in statements if 'kms:Decrypt' in s['Action'])
            self.assertEqual(kms['StringEquals']['kms:CallerAccount'], {'Ref': 'AWS::AccountId'})
            self.assertIn('kms:ViaService', kms['StringEquals'])
            self.assertEqual(kms['StringLike']['kms:EncryptionContext:aws:s3:arn'], [
                {'Fn::GetAtt': ['Files', 'Arn']}, {'Fn::Sub': '${Files.Arn}/*'}])

    def test_s3_delivery_is_exact_bucket_account_scoped_and_tls_required(self):
        bucket = self.resources['Files']
        self.assertEqual(bucket['DependsOn'], 'StorageQueuePolicy')
        self.assertEqual(bucket['Properties']['NotificationConfiguration']['QueueConfigurations'], [{
            'Event': 's3:ObjectCreated:*', 'Queue': {'Fn::GetAtt': ['StorageEvents', 'Arn']}}])
        allow, deny = self.resources['StorageQueuePolicy']['Properties']['PolicyDocument']['Statement']
        self.assertEqual(allow['Principal'], {'Service': 's3.amazonaws.com'})
        self.assertEqual(allow['Action'], 'sqs:SendMessage')
        self.assertEqual(allow['Condition']['StringEquals']['aws:SourceAccount'], {'Ref': 'AWS::AccountId'})
        self.assertEqual(deny['Effect'], 'Deny')
        self.assertEqual(deny['Condition'], {'Bool': {'aws:SecureTransport': 'false'}})

        # Resolve only pseudo parameters: no hidden dependency on Files/StorageEvents
        # may enter the pre-creation queue or redrive permission definitions.
        values = {'AWS::AccountId': '123456789012', 'AWS::Region': 'ap-south-1', 'AWS::Partition': 'aws',
                  'AWS::StackId': 'arn:aws:cloudformation:ap-south-1:123456789012:stack/prooflane/12345678-abcd-abcd-abcd-123456789012'}

        def resolve(node):
            if isinstance(node, str):
                return node
            if 'Ref' in node:
                return values[node['Ref']]
            if 'Fn::Split' in node:
                separator, value = node['Fn::Split']
                return resolve(value).split(separator)
            if 'Fn::Select' in node:
                index, sequence = node['Fn::Select']
                return resolve(sequence)[index]
            pattern, mappings = node['Fn::Sub']
            variables = {**values, **{key: resolve(value) for key, value in mappings.items()}}
            return re.sub(r'\$\{([^}]+)\}', lambda match: variables[match[1]], pattern)

        name = resolve(bucket['Properties']['BucketName'])
        self.assertLessEqual(len(name), 63)
        self.assertRegex(name, r'^[a-z0-9][a-z0-9-]+[a-z0-9]$')
        self.assertEqual(resolve(allow['Condition']['ArnEquals']['aws:SourceArn']), 'arn:aws:s3:::' + name)
        queue_name = resolve(self.resources['StorageEvents']['Properties']['QueueName'])
        self.assertLessEqual(len(queue_name), 80)
        source = self.resources['EventDeadLetter']['Properties']['RedriveAllowPolicy']['sourceQueueArns'][0]
        self.assertEqual(resolve(source), 'arn:aws:sqs:ap-south-1:123456789012:' + queue_name)

    def test_queue_retries_encryption_and_consumer_scope(self):
        queue = self.resources['StorageEvents']['Properties']
        dead = self.resources['EventDeadLetter']['Properties']
        for properties in [queue, dead]:
            self.assertTrue(properties['SqsManagedSseEnabled'])
            self.assertNotIn('KmsMasterKeyId', properties)
            self.assertFalse(properties.get('FifoQueue', False))
        self.assertEqual(queue['ReceiveMessageWaitTimeSeconds'], 20)
        self.assertEqual(queue['VisibilityTimeout'], 180)
        self.assertEqual(queue['RedrivePolicy'], {
            'deadLetterTargetArn': {'Fn::GetAtt': ['EventDeadLetter', 'Arn']}, 'maxReceiveCount': 5})
        self.assertGreater(dead['MessageRetentionPeriod'], queue['MessageRetentionPeriod'])
        self.assertEqual(dead['RedriveAllowPolicy']['redrivePermission'], 'byQueue')
        worker = self.resources['WorkerStoragePolicy']['Properties']['PolicyDocument']['Statement']
        consumer = next(s for s in worker if 'sqs:ReceiveMessage' in s['Action'])
        self.assertEqual(consumer['Resource'], {'Fn::GetAtt': ['StorageEvents', 'Arn']})
        api = self.resources['ApiStoragePolicy']['Properties']['PolicyDocument']['Statement']
        self.assertFalse(any(a.startswith('sqs:') for s in api for a in s['Action']))
        self.assertEqual(self.template['Outputs']['StorageEventQueueUrl']['Value'], {'Ref': 'StorageEvents'})

    def test_resource_dependencies_have_no_cycle(self):
        def references(node):
            found = set()
            if isinstance(node, dict):
                if node.get('Ref') in self.resources:
                    found.add(node['Ref'])
                if 'Fn::GetAtt' in node:
                    found.add(node['Fn::GetAtt'][0])
                value = node.get('Fn::Sub')
                pattern = value if isinstance(value, str) else value[0] if isinstance(value, list) else ''
                found |= {n.split('.')[0] for n in re.findall(r'\$\{([^}]+)\}', pattern)
                          if n.split('.')[0] in self.resources}
                for value in node.values():
                    found |= references(value)
            elif isinstance(node, list):
                for value in node:
                    found |= references(value)
            return found

        graph = {}
        for name, resource in self.resources.items():
            dependencies = resource.get('DependsOn', [])
            graph[name] = references(resource) | set([dependencies] if isinstance(dependencies, str) else dependencies)
        active, visited = set(), set()

        def visit(name):
            self.assertNotIn(name, active, 'CloudFormation resource dependency cycle')
            if name in visited:
                return
            active.add(name)
            for dependency in graph[name]:
                visit(dependency)
            active.remove(name)
            visited.add(name)

        for name in graph:
            visit(name)

    def test_minimal_review_never_claims_approval_or_spend_cap(self):
        report = review(mode='minimal')
        self.assertEqual(review()['mode'], 'minimal')
        with self.assertRaises(ValueError):
            review(mode='unknown')
        self.assertFalse(report['aws_actions_performed'])
        self.assertFalse(report['deployment_approved'])
        self.assertEqual(report['ecs_tasks'], [])
        self.assertEqual(report['total_fargate_vcpu'], 0)
        self.assertEqual(report['missing_parameters'], [])
        self.assertIn('no guaranteed $1 cap', report['scope'])
        self.assertTrue(any('KMS requests' in item for item in report['billable_components']))
        self.assertTrue(any('empty polling' in item for item in report['billable_components']))


if __name__ == '__main__':
    unittest.main()
