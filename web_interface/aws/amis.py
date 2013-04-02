from boto.ec2.connection import EC2Connection
AMI_OWNER = 389707735952 #That's me
AMI_NAME_STRING = 'Condor AMI'
AMI_VERSION_STRING = 'current'

def get_ami(ec2_connection, ami_name=AMI_NAME_STRING, ami_version=AMI_VERSION_STRING):
    assert isinstance(ec2_connection, EC2Connection)
    try:
        amis = ec2_connection.get_all_images(owners=[AMI_OWNER], filters={'tag:Name':ami_name, 'tag:Version':ami_version})
        assert len(amis) == 1
        return amis[0]
    except:
        raise
    
def get_current_ami(ec2_connection):
    return get_ami(ec2_connection)