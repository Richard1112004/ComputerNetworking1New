from transmit.Tracker_to_Node import *
from utils import *
import datetime
from threading import *
from collections import defaultdict
from transmit.data import Data
import time
import json
from TCPlimit import TCPlimit
from urllib.parse import urlparse, parse_qs
import hashlib
call = time.time()
class Tracker:
    def __init__(self):
        self.tracker_socket = set_socket(config.const["TRACKER_ADDR"][1])
        self.has_informed_tracker = defaultdict(bool)
        self.port = 22236
        self.file_owners_list = defaultdict(dict)
        self.send_freq_list = defaultdict(int)
        self.send_peer_list = []
        self.info_peers = []
        self.alive_nodes = set()
        self.dead_nodes = set()
        self.lookup_table = {}
    def search_file(self, msg: dict, addr: tuple, conn:socket.socket):
        print("----------------------")
        print(msg['metadata'])
        print("----------------------")
        print(f"Node{msg['node_id']} is searching for {msg['Id']}")
        # fix this
        matched_entries = self.file_owners_list[msg['Id']]

        tracker_response = Tracker_to_Node(dest_node_id=msg['node_id'],
                                        result=matched_entries)

        self.send_segment(sock=conn,
                          data=tracker_response.encode(),
                          )
    def create_info_peer(self, msg: dict, addr: tuple):
        info_peer = {
                'peer_id': msg['node_id'],
                'ip': addr[0],
                'port': addr[1],
                'metadata': msg['metadata'] 
        }
        
        self.info_peers.append(info_peer)
    def add_file_owner(self, msg: dict, addr: tuple):
        metadata = msg['metadata']
        # print(metadata)
        info = metadata['info']
        name_dict_list = [{"name": item["name"]} for item in info if "name" in item]
        new_info = [{k: v for k, v in item.items() if k != "name"} for item in info]
        metadata['info'] = new_info
        id = metadata['ID']
        entry = {
            'node_id': msg['node_id'],
            'addr': addr,
            'file_name': name_dict_list
        }
        # Nếu name chưa có trong file_owners_list, tạo mới một danh sách
        if id not in self.file_owners_list:
            self.file_owners_list[id] = {}  # Khởi tạo 'name' là một danh sách rỗng
            self.file_owners_list[id] = {
                'metadata': metadata,
                'peers': [entry]  # Khởi tạo 'peers' là một danh sách chứa entry
            }
        else:
            # Nếu name đã có trong file_owners_list
            existing_entry = self.file_owners_list[id]
            # Đảm bảo 'peers' là một danh sách, rồi thêm 'entry' vào đó
            
            existing_entry['peers'].append(entry)  # Thêm 'entry' vào danh sách 'peers'

        print(self.file_owners_list[id])
        # self.file_owners_list['peers'].append(json.dumps(entry))
        # if name not in self.file_owners_list['name']:
        #     self.file_owners_list['metadata'].append(metadata)
        
        if msg['node_id'] not in self.send_freq_list:
            self.send_freq_list[msg['node_id']] = 0  
        self.send_freq_list[msg['node_id']] += 1
        self.create_info_peer(msg, addr)
        if msg['node_id'] not in self.send_peer_list:
            self.send_peer_list.append(msg['node_id'])
       
        # print(self.file_owners_list)
        
        # name = json.dumps(msg['name'], sort_keys=True)  
        # metadata_key = json.dumps(msg['metadata'], sort_keys=True)  

        # if name not in self.file_owners_list:
        #     self.file_owners_list[name] = []  
        # self.file_owners_list[name].append(json.dumps(entry))
        # self.file_owners_list[name] = list(set(self.file_owners_list[metadata_key]))
        
        # if msg['node_id'] not in self.send_freq_list:
        #     self.send_freq_list[msg['node_id']] = 0  
        # self.send_freq_list[msg['node_id']] += 1
        # self.create_info_peer(msg, addr)
        # if msg['node_id'] not in self.send_peer_list:
        #     self.send_peer_list.append(msg['node_id'])
       
        # print(self.file_owners_list)
    # def remove_node(self, node_id: int, addr: tuple):
    #     entry = {
    #         'node_id': node_id,
    #         'addr': addr
    #     }
    #     self.has_informed_tracker.pop((node_id, addr), None)
        
    #     # Remove the node from file_owners_list
    #     for file_id, owners in list(self.file_owners_list.items()):
    #         self.file_owners_list[file_id] = [owner for owner in owners if owner['node_id'] != node_id]
    #         if not self.file_owners_list[file_id]:
    #             del self.file_owners_list[file_id]

    #     # Remove the node from send_peer_list
    #     if node_id in self.send_peer_list:
    #         self.send_peer_list.remove(node_id)

    #     # Remove the node from info_peers
    #     self.info_peers = [peer for peer in self.info_peers if peer['peer_id'] != node_id]
    #     self.dead_nodes.add(node_id)
    #     if node_id in self.alive_nodes:
    #         self.alive_nodes.remove(node_id)
    #     print(f"Node {node_id} removed from tracker.")
    def remove_node(self, node_id: int, addr: tuple):
        entry = {
            'node_id': node_id,
            'addr': addr
        }
        self.has_informed_tracker.pop((node_id, addr), None)
        
        # Remove the node from file_owners_list
        for file_id, owner_info in list(self.file_owners_list.items()):
            # Filter the 'peers' list to exclude the node with 'node_id'
            owner_info['peers'] = [peer for peer in owner_info['peers'] if peer['node_id'] != node_id]
            
            # If 'peers' becomes empty, remove the file_id from file_owners_list
            if not owner_info['peers']:
                del self.file_owners_list[file_id]

        # Remove the node from send_peer_list
        if node_id in self.send_peer_list:
            self.send_peer_list.remove(node_id)

        # Remove the node from info_peers
        self.info_peers = [peer for peer in self.info_peers if peer['peer_id'] != node_id]

        self.dead_nodes.add(node_id)
        if node_id in self.alive_nodes:
            self.alive_nodes.remove(node_id)

        print(f"Node {node_id} removed from tracker.")
        
    def generate_short_id(self, file_info):
        # Tạo short_id từ thông tin file
        file_str = f"{file_info['name']}{file_info['length']}{file_info['piece_length']}{file_info['pieces_count']}"
        short_id = hashlib.md5(file_str.encode()).hexdigest()[:8]
        # Lưu thông tin file vào bảng ánh xạ với short_id
        self.lookup_table[short_id] = file_info
        return short_id

    def parse_magnet_link(self, magnet_link):
        # Phân tích các thành phần của liên kết magnet
        parsed_url = urlparse(magnet_link)
        query_params = parse_qs(parsed_url.query)
        
        # Trích xuất ID
        metadata_id = query_params.get("xt", [""])[0].replace("urn:btih:", "")
        
        # Trích xuất IP
        metadata_ip = query_params.get("dn", [""])[0]
        
        # Trích xuất danh sách các tracker
        tracker_ids = query_params.get("tr", [])
        
        # Xây dựng lại metadata
        metadata = {
            "IP": metadata_ip,
            "info": [],
            "ID": metadata_id,
        }
        
        # Khôi phục lại metadata từ các short_id
        for short_id in tracker_ids:
            file_info = self.lookup_table.get(short_id, {"name": "Unknown", "length": 0, "piece_length": 0, "pieces_count": 0})
            metadata["info"].append(file_info)
        
        return metadata
    def handle(self, data: bytes, addr: tuple, conn: socket.socket):
        msg = Data.decode(data)
        mode = msg['mode']
        if mode == config.tracker_requests["UPLOAD"]:
            if (msg['metadata'] == '' and msg['magnet_link'] != ''):
                print(f"Node {msg['node_id']} requested tracker info with {msg['magnet_link']}")
                msg['metadata'] = self.parse_magnet_link(msg['magnet_link'])
                print(msg['metadata'])
            self.add_file_owner(msg=msg, addr=addr)
        if mode == config.tracker_requests["DOWNLOAD"]:
            self.search_file(msg=msg, addr=addr, conn=conn)
        # elif mode == config.tracker_requests_mode.UPDATE:
        #     self.update_db(msg=msg)
        if mode == config.tracker_requests["REQUEST"]:
            self.has_informed_tracker[(msg['node_id'], addr)] = True
            self.respond_tracker(msg['node_id'], conn=conn)
            print(f"Node {msg['node_id']} requested tracker info has {msg['downloaded_sum']} downloaded")
        elif mode == config.tracker_requests['EXIT']:
            self.remove_node(node_id=msg['node_id'], addr=addr)
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{current_time} - Node {msg['node_id']} in torrent")
    # def remove_node(self, node_id: int, addr: tuple):
    #     entry = {
    #         'node_id': node_id,
    #         'addr': addr
    #     }
    #     try:
    #         self.send_freq_list.pop(node_id)
    #     except KeyError:
    #         pass
    #     self.has_informed_tracker.pop((node_id, addr))
    #     node_files = self.file_owners_list.copy()
    #     for nf in node_files:
    #         if json.dumps(entry) in self.file_owners_list[nf]:
    #             self.file_owners_list[nf].remove(json.dumps(entry))
    #         if len(self.file_owners_list[nf]) == 0:
    #             self.file_owners_list.pop(nf)
    def send_segment(self, sock: socket.socket, data: bytes):
        # sock.connect((ip, track_port))
        # print(f"Connected to server at {ip}:{track_port}")
        segment = TCPlimit(
            data=data
        )
        encrypted_data = segment.data  
        sock.sendall(encrypted_data)
    def createResDict(self):
        torrent = {
            "fail" : "",
            "warning": "",
            "peers" : self.info_peers
        }
        if torrent['peers'] == []:
            torrent['warning'] = "No peers available"
        return torrent

    def respond_tracker(self, node_id: int, conn: socket.socket):
        torrent = self.createResDict()
        msg = Tracker_to_Node(dest_node_id=node_id, result=torrent)
        self.send_segment(sock=conn,data=msg.encode())

        # !
    # def check_nodes_periodically(self, interval: int):

    #     # Create a copy to safely iterate over
    #     has_informed_tracker_copy = self.has_informed_tracker.copy()

    #     for node, has_informed in has_informed_tracker_copy.items():
    #         node_id, node_addr = node
    #         if has_informed:
    #             # Node is alive, reset its informed status
    #             self.has_informed_tracker[node] = False
    #             self.alive_nodes.add(node_id)
    #             if node_id in self.dead_nodes:
    #                 self.dead_nodes.remove(node_id)
    #         else:
    #             # Node has not informed, mark it as dead
    #             self.dead_nodes.add(node_id)
    #             # self.remove_node(node_id=node_id, addr=node_addr)

    #     # Log active and inactive nodes if there were any changes
    #     if self.alive_nodes or self.dead_nodes:
    #         current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #         print(f"{current_time} - Node(s) {list(self.alive_nodes)} is in the torrent and Node(s) {list(self.dead_nodes)} have left.")

        # Schedule the next call using Timer
        # !
        # Timer(interval, self.check_nodes_periodically, args=(interval,)).start()
    # each client
    def handle_client(self, conn, addr):
        try:
            # with conn:
                threads = []
                while True:
                    data = conn.recv(config.const["BUFFER_SIZE"])
                    if not data:
                        break
                    t = Thread(target=self.handle, args=(data, addr, conn))
                    t.start()
                    threads.append(t)
                for t in threads:
                    t.join()
        except Exception as e:
            print(f"Exception handling client {addr}: {e}")
        finally:
            print(f"Connection closed with {addr}")
    def listen(self):
        # timer_thread = Thread(target=self.check_nodes_periodically, args=(config.const["TRACKER_TIME_INTERVAL"],))
        # timer_thread.daemon = True
        # timer_thread.start()
        self.tracker_socket.listen() 
        print(self.tracker_socket)
        # print(f"Tracker server listening on {config.const['TRACKER_ADDR'][1]}")

        
        while True:
            # Accept a new connection
            conn, addr = self.tracker_socket.accept()
            print(f"Connection established with {addr}")

            # Start a new thread to handle the connection
            client_thread = Thread(target=self.handle_client, args=(conn, addr))
            client_thread.daemon = True  # This ensures threads exit when main program exits
            client_thread.start()
    def run(self):
        hostname = socket.gethostname()
        hostip = get_host_default_interface_ip()

        # print("Tracker start at", config.const["TRACKER_ADDR"][1])
        print("Listening on: {}:{}:{}".format(hostname,hostip,self.port))
        t = Thread(target=self.listen())
        t.daemon = True
        t.start()
        t.join()
def get_host_default_interface_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
       s.connect(('8.8.8.8',1))
       ip = s.getsockname()[0]
    except Exception:
       ip = '127.0.0.1'
    finally:
       s.close()
    return ip    

if __name__ == '__main__':
    t = Tracker()
    t.run()