from lib.system import *
PYTHON_VERSION_MAJOR = 3
PYTHON_VERSION_MINOR = 5
check_python_version(PYTHON_VERSION_MAJOR, PYTHON_VERSION_MINOR)

import sys
import subprocess
import shlex
import json
from io import StringIO
import os
import argparse
from lib.shell import *
import time
from threading import Thread
from enum import Enum
from pprint import pprint

def kkkkquery(gerrit_id):
    ssh_cmd_string  = "ssh -p 29418 review-android.quicinc.com  gerrit query --current-patch-set --files --format=JSON " + str(gerrit_id)

    """
    p = subprocess.Popen(ssh_cmd_args,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         universal_newlines=True,
                         )
    """
    p = os.popen(ssh_cmd_string)
    output = p.readlines()[0]
    p.close()
    jsn_data = json.loads(output)
    print(jsn_data)


def check_exist_in_list(gerrit):
    with open("cmd", "r+") as f:
        line = f.readline()
        if gerrit not in line:
            print("%s not in hotfix list\n", gerrit)

class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None
        self._args=args

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args,
                                        **self._kwargs)

    def join(self, *args):
        Thread.join(self, *args)
        return self._return

class Qt(Enum):
    QUERY_ALL = 1
    QUERY_CURRENT = 2
    QUERY_PATCHSETS = 3

class Gerrit(object):

    def __init__(self, server, port, listfile):
        self.__server = server
        self.__port = port
        self.__listfile = listfile
        self.__gerrit_table = []
        self.__load()

    def __load(self):
        # the format of file might be quite different, need refine
        with open(self.__listfile, "r+") as f:
            line = f.readline()
            print(line)

            gerrit_list = line.split(",")
            #print(gerrit_list)
            for item in gerrit_list:
                list_temp = []
                #item = item.strip()[1: -1]
                item = item.strip()
                list_temp.append(item)
                list_temp.append("-1")
                self.__gerrit_table.append(list_temp)
            return

            while line:
                gerrit_patch = line.strip().split("/")
                print(gerrit_patch)
                if len(gerrit_patch) == 1:
                    gerrit_patch.append("-1")
                self.__gerrit_table.append(gerrit_patch)
                line = f.readline()

    def query_single(self, gerrit, query_type=Qt.QUERY_ALL, asyc=False):
        cmd = ["ssh", "-p", '%s' % self.__port, self.__server]
        if query_type == Qt.QUERY_CURRENT:
                cmd += ['gerrit query --current-patch-set --files --format=JSON', str(gerrit)]
        elif query_type == Qt.QUERY_PATCHSETS:
                cmd += ['gerrit query --patch-sets --files --format=JSON', str(gerrit)]
        else:
                cmd += ['gerrit query --current-patch-set --patch-sets --files --format=JSON', str(gerrit)]

        cmd = ' '.join(cmd)
        #print(cmd)
        if asyc:
            thread = bsh_async(cmd)
            return thread
        else:
            return bsh(cmd)

    def query_thread_v2(self):
        start_time =  time.time()
        threads = list()
        for gerrit in self.__gerrit_table:
            thread = ThreadWithReturnValue(target=self.query_single, args=(gerrit[0], Qt.QUERY_ALL, False))
            thread.start()
            threads.append(thread)

        # since it will block by the longest item, so join in one loop is fine
        for t in threads:
            print("================", time.time())
            output = t.join()
            # since the output includings to two dic, if loading directly, it will report error,
            # Fix me, ugly
            idx = output.rfind("{")
            str1 = output[: idx]
            str2 = output[idx :]
            dic = json.loads(str1)
            pprint(dic)
            print("author:", dic['owner']['name'])
            print("projects:", dic['project'])
            file_list = dic['currentPatchSet']['files']
            for item in range(1, len(file_list)):
                print("file:", file_list[item]['file'])
            #print(dic['currentPatchSet']['files'][-1]['file'])
            continue
            # Method2 looks like is more graceful
            json_txt = StringIO(output)
            for line in json_txt.readlines():
                dic = json.loads(line)
                #print(dic['owner']['name'])
                # only first line is valid, but still using for loop here
                print(json.dumps(dic, indent=4, sort_keys=True))
                #print(dic['currentPatchSet']['approvals'][8]['by']['email'])
                break

        print("parally2 query all gerrits, cost ", time.time() - start_time)

    def query_thread(self):
        start_time =  time.time()
        threads = list()
        for gerrit in self.__gerrit_table:
            thread = self.query_single(gerrit[0], Qt.QUERY_ALL, True)
            threads.append(thread)

        for t in threads:
            t.join()
        print("parallly query all gerrits, cost ", time.time() - start_time)

    def query_serial(self):
        start_time =  time.time()
        for gerrit in self.__gerrit_table:
            thread = self.query_single(gerrit[0], Qt.QUERY_ALL, False)

        print("serially query all gerrits, cost ", time.time() - start_time)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Probe Gerrit.')
    parser.add_argument('-s','--server',metavar='SERVER',default='review-android.quicinc.com',help='Gerrit server name')
    parser.add_argument('-p','--port',metavar='PORT',type=int,default=29418,help='Gerrit SSH port')
    parser.add_argument('-l','--listfile',metavar='LIST',default='gerrit_table.txt',help='Gerrit list table')
    args = parser.parse_args()

    if not os.path.exists(args.listfile):
        print("By default read gerrit list from file gerrit_table.txt, "
              "or use --listfile to specify list file name.")
        sys.exit(1)

    gerrit = Gerrit(args.server, args.port, args.listfile)
    #gerrit.query_thread()
    gerrit.query_thread_v2()
    #gerrit.query_serial()

