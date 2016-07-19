import argparse
import os
import sys
import pandas as pd
import numpy as np
import subprocess as subprocess
import time
import fileinput
import multiprocessing
import socket
import json

from itertools import cycle
from datetime import datetime

DOCKER_SOCKET = "/var/run/docker.sock"
CMD_DOCKER_GET_CONTAINER_LIST = "GET /containers/json HTTP/1.1\r\n\r\n"

UNIX_SOCKET = "unix"

class ContainerRepr:
    name = ''
    id = ''

class Request:

    def __init__(self, soc_type=UNIX_SOCKET, sock=None):
        if sock is None:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        else:
            self.sock = sock

    def connect(self, host):
        self.sock.connect(host)

    def get_response(self, command):

        response = []
        bytes_rcvd = 0
        total_bytes_snt = 0

        while total_bytes_snt < len(command):

            bytes_snt = self.sock.send(command[total_bytes_snt:])

            if bytes_snt == 0:
                raise RuntimeError("socket connection broken")
            total_bytes_snt = total_bytes_snt + bytes_snt

        while True:

            data_rcvd = self.sock.recv(4096)

            response.append(data_rcvd)
            # http responses end in '\r\n\r\n'
            if data_rcvd[-4:] == "\r\n\r\n":
                break

        # extract the http body. usually this should be something like
        #   STATUS LINE\r\n
        #   HEADERS\r\n\r\n
        #   BODY\r\n\r\n
        response = ''.join(response)
        for response_section in response.split("\r\n"):
            if (len(response_section) > 0) and (response_section[0] == "[" or response_section[0] == "{"):
                return response_section.rstrip()

        return ''

    def cleanup(self):
        self.sock.close()

def get_container_list(application):

    container_list = []

    requester = Request(UNIX_SOCKET, None)
    requester.connect(DOCKER_SOCKET)

    resp = requester.get_response("GET /containers/json HTTP/1.1\r\n\r\n")
    resp = json.loads(resp)

    for container in resp:
        if application in container['Image']:

            c = ContainerRepr()

            c.name = container['Names']
            c.id = container['Id']

            container_list.append(c)

    requester.cleanup()

    return container_list

def make_request((c_name, c_id, request)):

    # create a new connection to DOCKER_SOCKET
    requester = Request(UNIX_SOCKET, None)
    requester.connect(DOCKER_SOCKET)

    # make the request
    print "[docker-metrics.py::make_request()] fetching from " + str(c_name).rstrip()
    resp = requester.get_response(request)

    requester.cleanup()

def get_metrics(container_list):

    request_list = []

    for container in container_list:

        # HACK: for some reason, nova_ssh doesn't respond well to stats 
        # requests, so exclude it
        if str(container.name).rstrip() == "[u'/nova_ssh']":
            continue

        request = "GET /containers/" + container.id + "/stats?stream=false HTTP/1.1\r\n\r\n"
        request_list.append((
            str(container.name).rstrip(), 
            str(container.id).rstrip(), 
            request))

    # making API requests in a 'stop-and-wait' fashion takes a bit of time, 
    # so we use paralellization to make it quicker
    thread_pool = multiprocessing.Pool(6)

    start_time = time.time()

    thread_pool.map(make_request, request_list)
    # now we wait (hopefully a shorter time)
    thread_pool.close()
    thread_pool.join()

    elapsed_time = time.time() - start_time
    print "[docker-metrics.py::get_metrics()] request batch took " + str(elapsed_time) + " sec"

if __name__ == '__main__':

    # use an ArgumentParser for a nice CLI
    parser = argparse.ArgumentParser()

    # options (self-explanatory)
    parser.add_argument("--application", 
                         help="application to collect metrics from (e.g. \
                         '--application kolla')")

    args = parser.parse_args()

    container_list = get_container_list(args.application)
    get_metrics(container_list)

