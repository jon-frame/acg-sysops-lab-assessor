import boto3
import json

print('Loading function')
dynamo = boto3.client('dynamodb')


def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }


def lambda_handler(event, context):
    '''Demonstrates a simple HTTP endpoint using API Gateway. You have full
    access to the request and response payload, including headers and
    status code.

    To scan a DynamoDB table, make a GET request with the TableName as a
    query string parameter. To put, update, or delete an item, make a POST,
    PUT, or DELETE request respectively, passing in the payload to the
    DynamoDB API as a JSON body.
    '''
    #print("Received event: " + json.dumps(event, indent=2))


    # Snapshot Expectations - to use when checking 
    # expected_kms_key = a custom (customer-managed) key used on snapshot
    # expected_sg = an ingress rule allowing 3306 from 192.168.1.0/24
    # expected_param_group = custom param group with 'event_scheduler' enabled
    #


    # Get the relevant Snapshot Details
    operation = event['httpMethod']
    arn = event['queryStringParameters']['arn']
    client = boto3.client('rds')
    snaps_response = client.describe_db_snapshots()
    snapshot = [x for x in snaps_response['DBSnapshots'] if x['DBSnapshotArn'] == arn]
    db_identifier = snapshot[0]['DBInstanceIdentifier']
    snapshot_identifier = snapshot[0]['DBSnapshotIdentifier']
    #snapshot_details = client.describe_db_snapshot_attributes(DBSnapshotIdentifier=snapshot_identifier)
    db_instances = client.describe_db_instances(DBInstanceIdentifier=db_identifier)
    source_db_instance = db_instances['DBInstances'][0]

    #print(snapshot_details['DBSnapshotAttributesResult'])
    #print(db_instance['DBInstances'][0])
    
    # Check snapshot against challenge rules
    
    # KMS Encryption
    kms_id = snapshot[0]['KmsKeyId'] # just confirm it is present and not default key (?)
    key = boto3.client('kms').describe_key(KeyId=kms_id)
    if (key['KeyMetadata']['KeyManager'] == 'CUSTOMER'):
        print("CHECKS: Custom KMS Key has been used!")
    
    #print("DEBUG: KMS ID: ",kms_id)
    #if (db_engine == "mysql"):
    #    print("CHECKS: Correct Engine (mysql)")
    #if (db_engine == "mysql"):
    #    print("CHECKS: Correct Engine (mysql)")
    
    # DB Engine
    db_engine = snapshot[0]['Engine'] # check it is mysql
    #print("DEBUG:  Database Engine: ",db_engine)
    if (db_engine == "mysql"):
        print("CHECKS: Correct Engine (mysql)!")
    
    # SGs
    security_groups = source_db_instance['VpcSecurityGroups'] # may need to collate the ingress rules of all groups then check against that
    #print("DEBUG: Security Groups: ",security_groups)
    ingress_rules=boto3.client('ec2').describe_security_groups(GroupIds=[x['VpcSecurityGroupId'] for x in security_groups])
    all_ingress_groups = ingress_rules['SecurityGroups']
    ingress_rules = [x['IpPermissions'] for x in ingress_rules['SecurityGroups']] # check we are correct for port and ip
    matching_rule = [x for x in ingress_rules if x[0]['IpRanges'] == [{'CidrIp': '192.168.1.0/24'}] if x[0]['FromPort'] == 3306]
    if (len(matching_rule) >= 1):
        print("CHECKS: Found a correct ingress rule!")
    
    # Param Groups
    param_group = source_db_instance['DBParameterGroups'] # may need to iterate through all to confirm the relevant event_scheduler rule is in-place
    parameters_response = client.describe_db_parameters(DBParameterGroupName=param_group[0]['DBParameterGroupName'])
    tested_parameter = [x for x in parameters_response['Parameters'] if x['ParameterName'] == 'event_scheduler']
    if (tested_parameter[0]['ParameterValue'] == 'ON'):
        print("CHECKS: Found the correct parameter setting on parameter group")
    #print("DEBUG:  Parameter Groups: ",param_group)
    
    # TO DO
    # Run through all checks and as long as all pass then return 'Passed'
    # If function worked correctly but student made a mistake return 'Failed'
    # If there was a problem checking return 'Error'
    

