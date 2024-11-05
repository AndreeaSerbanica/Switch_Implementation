#!/usr/bin/python3
# import sys
import struct
# import wrapper
# import threading
# import time
from wrapper import send_to_link, get_switch_mac, get_interface_name

# Function that returns only the trunk ports
def only_truck_ports(vlan_map):
    trunk_ports = []
    for port in vlan_map:
        if vlan_map[port] == "T":
            trunk_ports.append(port)

    return trunk_ports

# Function that creates a BPDU packet
def create_bpdu_tag(root_bridge_id, sender_bridge_id, path_cost):
    dest_mac = bytes([0x01, 0x80, 0xc2, 0, 0, 0]) 
    switch_mac = get_switch_mac()
    root_bridge_to_pack = struct.pack("!H", root_bridge_id)
    sender_bridge_to_pack = struct.pack("!H", sender_bridge_id)
    path_cost_to_pack = struct.pack("!H", path_cost)
   
    packet = (dest_mac + switch_mac +
              root_bridge_to_pack + 
              sender_bridge_to_pack + 
              path_cost_to_pack)
    
    return packet

# Function that initializes the STP - from pseudocode
def initialize_stp(switch_prio, vlan_map):
    # Set trunk ports to BLOCKING
    port_states = {}
    designated_ports = []
    for port in vlan_map:
        if vlan_map[port] == "T":
            port_states[port] = "BLOCKING"

    # Initialize bridge IDs and path cost
    priority_value = switch_prio
    own_bridge_ID = priority_value
    root_bridge_ID = own_bridge_ID
    root_path_cost = 0

    # If the switch is the root bridge, set all ports to DESIGNATED_PORT
    if own_bridge_ID == root_bridge_ID:
        for port in vlan_map:
            if vlan_map[port] != "T":
                port_states[port] = "LISTENING"
                designated_ports.append(port)

    return port_states, own_bridge_ID, root_bridge_ID, root_path_cost,designated_ports


class BPDU:
    def __init__(self, switch_prio, vlan_map, interfaces):
        self.interfaces_states, self.own_bridge_ID, self.root_bridge_ID, self.root_path_cost, self.designated_ports = initialize_stp(switch_prio, vlan_map)
        self.root_port = -1
        self.trunk_ports = only_truck_ports(vlan_map)
        self.vlan_map = vlan_map
        self.interfaces = interfaces
    
    # Function that processes the BPDU packet - from pseudocode
    def process_bdpu_packet(self, interface, data, length):
        # print(f"Interfaces states from process_bdpu_packet: {self.interfaces_states}")

        root_bridge_ID, sender_bridge_ID, sender_path = struct.unpack("!3H", data[12:18])
         
        if root_bridge_ID < self.root_bridge_ID:
            self.root_bridge_ID = root_bridge_ID
            self.root_path_cost = sender_path + 10
            self.root_port = interface
            
            # if we were the Root Bridge:
            # set all interfaces not to hosts to blocking except the root port
            if self.own_bridge_ID == self.root_bridge_ID:
               for i in self.interfaces: # interfaces = {0,1,2}  #design = {rr ...}
                    if self.vlan_map[get_interface_name(i)] == "T" and interface != i:
                        self.interfaces_states[i] = "BLOCKING"
                        self.designated_ports.remove(get_interface_name(i))

                        
            if self.interfaces_states[get_interface_name(self.root_port)] == "BLOCKING":
                self.interfaces_states[get_interface_name(self.root_port)] = "LISTENING"

            
            # Update and forward this BPDU to all other trunk ports with:
            #     sender_bridge_ID = own_bridge_ID
            #     sender_path_cost = root_path_cost
            bpdu_packet = create_bpdu_tag(self.root_bridge_ID, self.own_bridge_ID, self.root_path_cost)

            for i in self.interfaces:
                if get_interface_name(i) in self.trunk_ports and i != interface:
                    len_bdpu = len(bpdu_packet)
                    send_to_link(i, len_bdpu, bpdu_packet)
        
        elif root_bridge_ID == self.root_bridge_ID:
            if interface == self.root_port and  sender_bridge_ID + 10 < self.root_path_cost:
                self.root_path_cost = sender_path + 10
            
            elif interface != self.root_port:
                if sender_path > self.root_path_cost:
                    if get_interface_name(interface) not in self.designated_ports:
                        self.designated_ports.append(get_interface_name(interface))
                        self.interfaces_states[get_interface_name(interface)] = "LISTENING"
                        # print(f"Adding interface {interface} to designated ports")
        
        elif sender_bridge_ID == self.own_bridge_ID:
            self.interfaces_states[get_interface_name(interface)] = "BLOCKING"
            port = get_interface_name(interface)
            # print(f"Port {interface} set to BLOCKING due to loop prevention.")
            self.designated_ports.remove(port)
        # else:
        #     print(f"Discarding BPDU on interface {interface}: does not improve current root path.")

        if self.own_bridge_ID == self.root_bridge_ID:
            for i in self.interfaces:
                if i !=self.root_port and get_interface_name(i) in self.trunk_ports:
                    self.interfaces_states[get_interface_name(i)] = "LISTENING"
                    self.designated_ports.append(get_interface_name(i))
        

    def interfaces_that_work(self):
        work_interface = []

        for i in self.interfaces:
            if self.interfaces_states[get_interface_name(i)] != "BLOCKING":
                work_interface.append(i)

        return work_interface
