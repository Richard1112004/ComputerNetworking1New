# Computer Networking Project

This project simulates a peer-to-peer (P2P) file sharing network. It includes the implementation of nodes and a tracker to manage the network. Nodes can join the network, search for files, download files from other nodes, and periodically inform the tracker of their status.

## Components

- **Node**: Represents a peer in the network. Nodes can request files from other nodes, share files, and communicate with the tracker.
- **Tracker**: Manages the network by keeping track of active nodes and the files they share. It helps nodes find peers that have the requested files.

## How to Run

### Running the Tracker

To start the tracker, run the following command:

    python3 tracker.py


### Running the Node
To start the node, run the following command:

    python3 node2.py -s <tracker_id> -p <tracker_port> (22236 is default) <node_id>

example: python3 node2.py -s 192.168.56.106 -p 22236 1

nodeVMnew.py is using for VM on virtual box for presentation. You can change the name of the file if you want.


You can choose three option:
    
    upload <URL in your machine>
    download <ID>
    exit

- **upload** to upload your torrent into this app
- **download** to download the other 's torrent into your machine
- **exit** to stop the process


I hope you can use it easily. If you have any difficult, do not hesitate to contact me through my email. :smile: