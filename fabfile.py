from fabric import task
from invoke.exceptions import UnexpectedExit


@task(
    help={
        'username': 'User name to create, e.g., nick',
        'full-name': 'Name to give to the user, e.g., Nick Durant',
        'public-key-file': 'Path to the file to upload, e.g., ~/ssh_keyfiles/nick.pub',
        'sudoer': 'If Sudo access should be given, e.g., True',
    }
)
def add_user(connection, username, full_name, public_key_file, sudoer=False):
    """
    Add a user to a server, optionally giving them sudo access.

    Tested with Ubuntu 20.04.3 LTS, using an official AWS EC2 AMI.

    Example usage:

    If we want to add the user "nick" to the host "middle-prod-2", and had the user's ssh keyfile at
    /Users/adam/ssh_keyfiles/nick.pub, we would use the following command:

    fab -H middle-prod-2 add-user --username=nick --full-name="Nick Durant" --public-key-file=/Users/adam/ssh_keyfiles/nick.pub --sudoer
    """
    print(f'Executing add_user with username={username} full_name={full_name} public_key_file={public_key_file} sudoer={sudoer}. OK?')
    ok = input()
    if not ok:
        print('Not OK, exiting now')
        return 
    else:
        print('Proceeding...')

    public_key_file = open(public_key_file, 'r')
    public_key_str = public_key_file.readlines()[0]
    public_key_file.close()

    print('Create the user...')
    try:
        connection.sudo("adduser --disabled-password --GECOS \"{geos}\" {username}".format(geos=full_name, username=username))
    except UnexpectedExit as e:
        if f"adduser: The user `{username}' already exists." in e.result.stderr:
            print('...User already created, OK!')
            pass
        else:
            raise
    else:
        print('...user created')

    print('Set the password to "password"...')
    connection.sudo("echo '{username}:password'|sudo chpasswd".format(username=username))
    print('...password set')

    if sudoer:
        print('Add them as a sudo-er...')
        connection.sudo("usermod -a -G sudo {username}".format(username=username))
        print('...sudo-er set')
    else:
        print('--sudoer option not set, no need to add as sudoer')

    print("Make them expire their password...")
    connection.sudo("chage -d 0 %s" % username)
    print("...password expire set")

    print("Make a new directory called .ssh")
    ssh_dir_name = "/home/{username}/.ssh".format(username=username)
    try:
        connection.sudo("mkdir {ssh_dir_name}".format(ssh_dir_name=ssh_dir_name))
    except UnexpectedExit as e:
        if f"mkdir: cannot create directory ‘/home/{username}/.ssh’: File exists" in e.result.stderr:
            print("... .ssh directory already created, OK!")
        else:
            raise
    connection.sudo("chown {username}:{username} {ssh_dir_name}".format(username=username, ssh_dir_name=ssh_dir_name))
    print("... .ssh directory set")

    print("Insert the user's private key")
    authorized_keys_filename = f"/home/{username}/.ssh/authorized_keys"
    connection.sudo(f"sh -c 'echo \"{public_key_str}\" > {authorized_keys_filename}'")
    connection.sudo(f"chown {username}:{username} {authorized_keys_filename}")
    connection.sudo(f"chmod 644 {authorized_keys_filename}")
    print("... private key set")

    print("Set the directory to read only")
    connection.sudo("chmod 700 {ssh_dir_name}".format(ssh_dir_name=ssh_dir_name))
    print("...directory chmod set")
