import argparse
import mmap
import uuid
from transmit.data import Data
from transmit.Node_to_Tracker import *
from transmit.chunk_messages import *
from transmit.Node_to_Node import *
from threading import *
from utils import *
import time
from TCPlimit import TCPlimit
import datetime
from collections import defaultdict
import os
import math
from builtins import enumerate
import hashlib
import json
# from flask import Flask, request, jsonify
from operator import itemgetter
from itertools import groupby
from urllib.parse import urlparse, parse_qs
call = time.time()
count = 0
class Node:
    def __init__(self, node_id: int, recieve_port: int, send_port: int, tracker_ip: int):
        self.tracker_ip =  tracker_ip
        self.node_id = node_id
        self.downloaded_files= {}
        self.recieve_socket = set_socket(recieve_port)
        self.send_socket = set_socket(send_port) 
        self.send_port = send_port
        self.downloaded_sum = self.load_downloaded_sum()
        self.lookup_table = {}
    def send_segment(self, sock: socket.socket, data: bytes):
        # sock.connect((ip, track_port))
        # print(f"Connected to server at {ip}:{track_port}")
        segment = TCPlimit(
            data=data
        )
        encrypted_data = segment.data  
        sock.sendall(encrypted_data)
    
    
    def inform_tracker_periodically(self, interval: int):
        # Update and print the current time for each call
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{current_time} - Node {self.node_id} is still alive in the torrent!")
        global count
        if count != 0:
            msg = Node_to_Tracker(node_id=self.node_id,
                                mode=config.tracker_requests["REQUEST"],
                                metadata="", Id = "" )

            self.send_segment(sock=self.send_socket,
                            data=msg.encode())

        # Schedule the next call
        count = count+1
        Timer(interval, self.inform_tracker_periodically, args=(interval,)).start()
    def go_torrent(self):
        try:
            msg = Node_to_Tracker(node_id=self.node_id,
                                mode=config.tracker_requests["REQUEST"],
                                metadata="", Id="", downloaded_sum=self.downloaded_sum)

            # addr = tuple(config.const["TRACKER_ADDR)
            addr = tuple((server_ip, port))
            ip, track_port = addr
            print(ip, track_port)
            # sock = socket.socket()
            self.send_socket.connect((ip, track_port))

            # self.send_socket.connect((ip, track_port))
            print(f"Connected to server at {ip}:{track_port}")
            self.send_segment(sock=self.send_socket,
                            data=Data.encode(msg))
            data = self.send_socket.recv(config.const["BUFFER_SIZE"])
            msg = Data.decode(data)
            return msg
        except Exception as e:
            print({'fail': "failed to connect to the tracker"})
            print(f"Error: {e}")
            exit(1)
    def create_info_dict(self, file_name):
        with open(file_name, 'rb') as file:
            file_data = file.read()
        info_dict = {
                # 'name': os.path.basename(file_name),
                'name': file_name,

                'length': len(file_data),
                'piece length': config.const['CHUNK_PIECES_SIZE'],
                'pieces_count': math.ceil(len(file_data)/config.const['CHUNK_PIECES_SIZE']) 
        }
        return info_dict
    def hash_file(self, file_path):
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def hash_folder(self, folder_path):
        # Use a separate hasher for the entire folder
        folder_hasher = hashlib.sha256()
        for root, dirs, files in os.walk(folder_path):
            for file in sorted(files):  # Sort to ensure consistent order
                file_path = os.path.join(root, file)
                file_hash = self.hash_file(file_path)
                # Update the folder hash with the file path and file hash
                folder_hasher.update(file_path.encode())  # Include file path
                folder_hasher.update(file_hash.encode())  # Include file hash
        # Return the final hash as a string
        return folder_hasher.hexdigest()
    def generate_short_id(self, file_info):
        # Tạo short_id từ thông tin file
        file_str = f"{file_info['name']}{file_info['length']}{file_info['piece length']}{file_info['pieces_count']}"
        short_id = hashlib.md5(file_str.encode()).hexdigest()[:8]
        # Lưu thông tin file vào bảng ánh xạ với short_id
        self.lookup_table[short_id] = file_info
        return short_id


    def upload_Magnet(self, directory_path):
        metadata = self.get_DotTorrent(directory_path)
        # Build the magnet link
        magnet_link = f"magnet:?xt=urn:btih:{metadata['ID']}"

        # Optionally add the name (dn) and tracker (tr)
        if "IP" in metadata:
            magnet_link += f"&dn={metadata['IP']}"
        if "info" in metadata:
            if isinstance(metadata['info'], list):
                for tracker in metadata['info']:
                    short_id = self.generate_short_id(tracker)
                    magnet_link += f"&tr={short_id}"
            else:
                short_id = self.generate_short_id(metadata['info'])
                magnet_link += f"&tr={short_id}"
        msg = Node_to_Tracker(node_id=self.node_id,
                            mode=config.tracker_requests["UPLOAD"],
                            metadata="",Id="", magnet_link=magnet_link)

        self.send_segment(sock=self.send_socket,
                            data=msg.encode())  
        
        t = Thread(target=self.listen, args=())
        t.daemon = True
        t.start()
        
    def get_DotTorrent(self, directory_path):
        files = os.listdir(directory_path)
        info_arr = []
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        for file in files:
            full_path = os.path.join(directory_path, file)
            info_arr.append(self.create_info_dict(full_path)) 
        torrent = {
            # "IP" :ip,
            # "port": self.send_port,
            "info" : info_arr,
            "ID": self.hash_folder(directory_path)
        }
        return torrent
    def upload(self, directory_path):
        metadata = self.get_DotTorrent(directory_path)
        msg = Node_to_Tracker(node_id=self.node_id,
                            mode=config.tracker_requests["UPLOAD"],
                            metadata=metadata,Id="")

        self.send_segment(sock=self.send_socket,
                            data=msg.encode())  
        
        # if self.is_in_send_mode:    # has been already in send(upload) mode
        #     log_content = f"Some other node also requested a file from you! But you are already in SEND(upload) mode!"
        #     # log(node_id=self.node_id, content=log_content)
        #     return
        # else:
        #     self.is_in_send_mode = True
        #     log_content = f"You are free now! You are waiting for other nodes' requests!"
        #     log(node_id=self.node_id, content=log_content)
        t = Thread(target=self.listen, args=())
        t.daemon = True
        t.start()
    
    def handle_client(self, conn, addr):
        with conn:
            data = conn.recv(config.const["BUFFER_SIZE"])
            # Process the data in a new thread
            msg = Data.decode(data)
            self.send_chunk(msg, addr, conn)
        print(f"Connection closed with {addr}")
        
    def listen(self):
        listen_socket = set_socket(self.send_port)
        listen_socket.listen()
        while True:
            conn, addr = listen_socket.accept()
            print(f"Connection established with {addr}")

            # Start a new thread to handle the connection
            client_thread = Thread(target=self.handle_client, args=(conn, addr))
            client_thread.daemon = True  # This ensures threads exit when main program exits
            client_thread.start()
                    
                    
    def download(self, id: str):
            print("Downloading")
            tracker_response = self.search_torrent(id = id)
            print("_--------------------------------------------------")
            print(tracker_response)
            file_owners = tracker_response['result']
            print(file_owners)
            self.split_file_owners(file_owners=file_owners, id=id)
    
    def search_torrent(self, id: str) -> dict:
        msg = Node_to_Tracker(node_id=self.node_id,
                           mode=config.tracker_requests['DOWNLOAD'],
                           metadata="", Id=id)
        self.send_segment(sock=self.send_socket,
                          data=msg.encode(),
                         )
        # now we must wait for the tracker response
        while True:
            data, addr = self.send_socket.recvfrom(config.const['BUFFER_SIZE'])
            tracker_msg = Data.decode(data)
            # print(tracker_msg)
            return tracker_msg
    def split_file_to_chunks(self, file_path: str, rng: tuple) -> list:
        with open(file_path, "r+b") as f:
            mm = mmap.mmap(f.fileno(), 0)[rng[0]: rng[1]]
            # we divide each chunk to a fixed-size pieces to be transferable
            return [mm[p: p + (config.const['CHUNK_PIECES_SIZE']//10)] for p in range(0, rng[1] - rng[0], (config.const['CHUNK_PIECES_SIZE']//10))]
    def send_chunk(self, msg, add, conn:socket.socket):
        # file_path = f"{config.directory.node_files_dir}node{self.node_id}/{filename}"
        file_path = msg['filename']
        chunk_pieces = self.split_file_to_chunks(file_path=file_path,
                                                 rng=msg['range'])
        # print((msg['src_node_id'], msg['dest_node_id']))

        for idx, p in enumerate(chunk_pieces):
            chunk_msg = ChunkSharing(src_node_id=self.node_id,
                               dest_node_id=msg['src_node_id'],
                               filename=msg['filename'],
                               range=msg['range'],
                               idx=idx,
                               chunk=p)
            # ! ///////
            # print("-------------------------------------------------")
            # print(idx)
            # print("-------------------------------------------------")
            # ! ///////
            # log_content = f"The {idx}/{len(chunk_pieces)} has been sent!"
            # log(node_id=self.node_id, content=log_content)
            self.send_segment(sock=conn,
                              data=Data.encode(chunk_msg)
                              )
            time.sleep(0.01)
        
        # now let's tell the neighboring peer that sending has finished (idx = -1)
        end_msg = ChunkSharing(src_node_id=self.node_id,
                           dest_node_id=msg['src_node_id'],
                           filename=msg['filename'],
                           range=msg['range'])
        self.send_segment(sock=conn,
                          data=Data.encode(end_msg)
                          )

        print(f"The process of sending a chunk to node{msg['src_node_id']} of file {msg['filename']} has finished!")
        # log(node_id=self.node_id, content=log_content)

        # msg = Node_to_Tracker(node_id=self.node_id,
        #                    mode=config.tracker_requests_mode.UPDATE,
        #                    filename=filename)

        # self.send_segment(sock=temp_sock,
        #                   data=Data.encode(msg),
        #                   addr=tuple(config.constants.TRACKER_ADDR))

        # free_socket(temp_sock)

    def receive_chunk(self, filename: str, range: tuple, file_owner: dict):
        # print("aaaddddddddddddddddddddddddd")
        dest_node = file_owner['node_id']
        # print(file_owner)
        # we set idx of ChunkSharing to -1, because we want to tell it that we
        # need the chunk from it
        
        msg = ChunkSharing(src_node_id=self.node_id,
                           dest_node_id=dest_node,
                           filename=filename,
                           range=range)
        temp_port = create_random_port()
        temp_socket = set_socket(temp_port)
        # print(file_owner)
        print("*******************************************")
        print(file_owner['addr'][0], file_owner['addr'][1])
        temp_socket.connect((file_owner['addr'][0], file_owner['addr'][1]))
        self.send_segment(sock=temp_socket,
                          data=msg.encode()
                          )
        # print(f"I sent a request for a chunk of {0} for node{1}.format(filename, dest_node")
        #! /////
        print(f"I   a a request for a chunk of {filename} for node {dest_node}.")
        i = math.ceil((range[1] - range[0])  / (int)(config.const['CHUNK_PIECES_SIZE']//10)) 
        print(i)
        while i:
            data, addr = temp_socket.recvfrom(config.const['BUFFER_SIZE'])
            
            if not data:
                print("Received empty data, skipping decoding.")
                i -= 1
                continue
            # print("-------------------------------------------------")
            # print(f"I receive {i}th" )
            # print("-------------------------------------------------")
            try:
                msg = Data.decode(data)
            except EOFError:
                print("EOFError: Incomplete data received, skipping.")
                continue


            i -= 1
            self.downloaded_files[filename].append(msg)

        print(f"I has received all the chunks of {filename} from node {dest_node}.")
        # ! ////////
    
    # thread chạy nhiều file đồng bộ
    def down(self, info1, peers):
             # 2. Now, we know the size, let's split it equally among peers to download chunks of it from them
        step = info1['length'] / len(peers)
        chunks_ranges = [(round(step*i), round(step*(i+1))) for i in range(len(peers))]

        # 3. Create a thread for each neighbor peer to get a chunk from it
        # print(chunks_ranges)
        self.downloaded_files[info1['name']] = []
        neighboring_peers_threads = []
        # print("donald trump")
        # temp_port = create_random_port()
        # temp_socket = set_socket(temp_port)
        # dest_node = peers[0]['node_id']
        # msg = ChunkSharing(src_node_id=self.node_id,
        #                    dest_node_id=dest_node,
        #                    filename=info1['name'],
        #                    range=range)
        # temp_port = create_random_port()
        # temp_socket = set_socket(temp_port)
        # print(file_owner)
        # temp_socket.connect((peers[0]['addr'][0], peers[0]['addr'][1]))
        # self.send_segment(sock=temp_socket,
        #                   data=msg.encode()
        #                   )

        for idx, obj in enumerate(peers):
            # self.receive_chunk(info1['name'], chunks_ranges[idx], obj)
            
            # print(peers)
            print("-------------------------------------------------")
            print(chunks_ranges[idx], obj)
            print("-------------------------------------------------")
            t = Thread(target=self.receive_chunk, args=(info1['name'], chunks_ranges[idx], obj))
            t.daemon = True
            t.start()
            neighboring_peers_threads.append(t)

        for t in neighboring_peers_threads:
            t.join()
        


        sorted_chunks = self.sort_downloaded_chunks(filename=info1['name'])
        # print("sorted_chunks")
        # print(sorted_chunks)
        # 5. Finally, we assemble the chunks to re-build the file
        total_file = []
        file_name = os.path.basename(info1['name'])
        # parent_dir = os.path.basename(os.path.dirname(info1['name']))
        
        # os.makedirs(parent_dir, exist_ok=True)
        file_path = os.path.join("/mnt/c/Clone/Deploy/ComputerNetworking1ydownload", file_name)
        for chunk in sorted_chunks:
            for piece in chunk:
                total_file.append(piece["chunk"])
        self.reassemble_file(chunks=total_file, file_path=file_path)
        print(f"{file_path} has successfully downloaded and saved in my files directory.")
            # self.files.append(filename)

        


        # print("finished")     
    def reassemble_file(self, chunks: list, file_path: str):
        
        # os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "bw+") as f:
            for ch in chunks:
                f.write(ch)
            f.flush()
            f.close()
    def sort_downloaded_chunks(self, filename: str) -> list:
        sort_result_by_range = sorted(self.downloaded_files[filename],
                                      key=itemgetter("range"))
        group_by_range = groupby(sort_result_by_range,
                                 key=lambda i: i["range"])
        sorted_downloaded_chunks = []
        for key, value in group_by_range:
            value_sorted_by_idx = sorted(list(value),
                                         key=itemgetter("idx"))
            sorted_downloaded_chunks.append(value_sorted_by_idx)

        return sorted_downloaded_chunks 
    def exit_torrent(self):
        msg = Node_to_Tracker(node_id=self.node_id,
                           mode=config.tracker_requests['EXIT'],
                           metadata="", Id="")
        self.send_segment(sock=self.send_socket,
                          data=Data.encode(msg),
                          )
        self.save_downloaded_sum()
        free_socket(self.send_socket)
        free_socket(self.recieve_socket)

        print(f"Stopped")       
    def split_file_owners(self, file_owners: list, id: str):
        # owners = []
        # for owner in file_owners:
        #     if owner[0]['node_id'] != self.node_id:
        #         owners.append(owner)
        if file_owners == {}:
            print(f"No one has {id}")
            return
        print("-----------------------------------start---------------------------------")
        print(file_owners)
        print("-----------------------------------end---------------------------------")
        # ? We do not implement algorithms here 
        # sort owners based on their sending frequency
        # owners = sorted(owners, key=lambda x: x[1], reverse=True)

        # to_be_used_owners = owners[:config.constants.MAX_SPLITTNES_RATE]
        
        # 1. first ask the size of the file from peers
        # print(file_owners)
        print(f"You are going to download {id} from Node(s) {[o['node_id'] for o in file_owners['peers']]}")
        # print("aaa")
                # log(node_id=self.node_id, content=log_content)
        file_threads = []
        # file_count = len(file_owners[0]['metadata']['info'])
        
        # chia thread dựa trên số file trong torrent
        # /////
        for i in file_owners['metadata']['info']:
            self.downloaded_sum += i['length']  
            thread = Thread(target = self.down, args=(i, file_owners['peers'],)) 
            # thread.daemon=True
            thread.start()
            file_threads.append(thread)
        for t in file_threads:
            t.join()
        # ///////
        print("-----------------------------------finished---------------------------------")
        print(self.downloaded_sum)
        # 4. Now we have downloaded all the chunks of the file. It's time to sort them.

        # # 5. Finally, we assemble the chunks to re-build the file
        # total_file = []
        # file_path = f"{config.directory.node_files_dir}node{self.node_id}/{filename}"
        # for chunk in sorted_chunks:
        #     for piece in chunk:
        #         total_file.append(piece["chunk"])
        # self.reassemble_file(chunks=total_file,
        #                      file_path=file_path)
        # log_content = f"{filename} has successfully downloaded and saved in my files directory."
        # log(node_id=self.node_id, content=log_content)
        # self.files.append(filename)
    def save_downloaded_sum(self):
        with open(f"node_{self.node_id}_downloaded_sum.txt", "w") as f:
            f.write(str(self.downloaded_sum))

    def load_downloaded_sum(self):
        try:
            with open(f"node_{self.node_id}_downloaded_sum.txt", "r") as f:
                return int(f.read())
        except FileNotFoundError:
            return 0  
def run (args):
    print('Connecting to: {}:{:d}'.format(args.s, args.p))

    node = Node(node_id=args.node_id,recieve_port=args.p, send_port=create_random_port(), tracker_ip= args.s)
    print("Starting")
    print(node.downloaded_sum)
    metadata = node.go_torrent()
    print("Completed")
    print(metadata)
    print("You're in program")
    timer_thread = Thread(target=node.inform_tracker_periodically, args=(config.const["NODE_TIME_INTERVAL"],))
    timer_thread.daemon = True
    timer_thread.start()
    print("ENTER YOUR COMMAND!")
    while True:
        command = input()
        mode, torrent = parse_command(command)

        #################### send mode ####################
        if mode == 'upload_Magnet':
            t = Thread(target=node.upload_Magnet, args=(torrent,))
            t.daemon = True
            t.start()
        elif mode == 'upload':
            t = Thread(target=node.upload, args=(torrent,))
            t.daemon = True
            t.start()
        ################### download mode ####################
        elif mode == 'download':                
            # phuc hung
            t = Thread(target=node.download, args=(torrent,))
            t.daemon = True
            t.start()
        # update C:\\Clone\\ddd\\ComputerNetworking1\\node\\node1\\hung.txt
        #################### exit mode ####################
        elif mode == 'exit':
            node.exit_torrent()
            exit(0)
        else:
            print("Try again. Mode(upload, download, exit) <space> File_name")
        
if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser(
                        prog='Client',
                        description='Connect to tracker',
                        epilog='!!!It requires the server is running and listening!!!')
    # parser.add_argument('node_id', type=int)
    parser.add_argument('-s', required=True, metavar="SERVER_IP",help='Địa chỉ IP của server')
    parser.add_argument('-p', type=int, required=True,metavar='SERVER_PORT', help='Cổng của server')

    parser.add_argument('node_id', type=int)
    node_args = parser.parse_args()
    server_ip = node_args.s
    port = node_args.p
    
    run(args=node_args)