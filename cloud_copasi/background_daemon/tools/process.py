#Module for executing external commands using subprocess, but with a custom timeout
#Note: Only works on UNIX-like systems
#Written by Bjorn Lindqvist, adapted from an example by Alex Martelli
#Source: http://stackoverflow.com/questions/1191374/subprocess-with-timeout
#Licensed under Creative Commons Attribution-ShareAlike 2.5 Generic (CC BY-SA 2.5)
#http://creativecommons.org/licenses/by-sa/2.5/

#TODO:Is this module really needed anymore? probably....

from os import kill
from signal import alarm, signal, SIGALRM, SIGKILL
from subprocess import PIPE, Popen

def run(args, cwd = None, shell = False, kill_tree = True, timeout = -1):
    '''
    Run a command with a timeout after which it will be forcibly
    killed.
    '''
    class Alarm(Exception):
        pass
    def alarm_handler(signum, frame):
        raise Alarm
    p = Popen(args, shell = shell, cwd = cwd, stdout = PIPE, stderr = PIPE)
    if timeout != -1:
        signal(SIGALRM, alarm_handler)
        alarm(timeout)
    try:
        stdout, stderr = p.communicate()
        if timeout != -1:
            alarm(0)
    except Alarm:
        pids = [p.pid]
        if kill_tree:
            pids.extend(get_process_children(p.pid))
        for pid in pids:
            kill(pid, SIGKILL)
        return -9, '', ''
    return p.returncode, stdout, stderr

def get_process_children(pid):
    p = Popen('ps --no-headers -o pid --ppid %d' % pid, shell = True,
              stdout = PIPE, stderr = PIPE)
    stdout, stderr = p.communicate()
    return [int(p) for p in stdout.split()]

if __name__ == '__main__':
    print(run('find /', shell = True, timeout = 3))
    print (run('find', shell = True))
