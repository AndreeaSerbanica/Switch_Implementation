#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name
from stp import BPDU, create_bpdu_tag # type: ignore


def parse_ethernet_header(data):
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]
    vlan_id = -1
    
    # Check for VLAN tag (0x8200 for custom implementation)
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id


def create_vlan_tag(vlan_id):
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)


def send_bdpu_every_sec(bdpu_pack: BPDU, interfaces):
    while True:
        # Placeholder for BDPU
        if bdpu_pack.own_bridge_ID == bdpu_pack.root_bridge_ID:
            for i in interfaces:
                if get_interface_name(i) in bdpu_pack.trunk_ports:
                    bpdu_data = create_bpdu_tag(bdpu_pack.root_bridge_ID, bdpu_pack.own_bridge_ID, 0)
                    send_to_link(i, len(bpdu_data), bpdu_data)

        time.sleep(1)


# Function to check if the MAC address is unicast
def is_unicast(mac):
    first_byte = int(mac[:2], 16)
    return (first_byte & 1) == 0


def read_config_file(switch_id, interfaces):

    vlans_config = {}
    config_file = f"configs/switch{switch_id}.cfg"

    f_in = open(config_file, "r")
    priority = int(f_in.readline())

    for _ in interfaces:
        config = f_in.readline().rstrip("\n").split(" ")
        vlans_config[config[0]] = config[1]

    f_in.close()

    return priority, vlans_config


def send_with_vlan(vlan_id, vlan_src, vlan_dest, out_interface, length, data):
    if vlan_id == -1:
        vlan_id = vlan_src
        if vlan_dest == "T": # acces -> trunk
            tagged_frame = data[0:12] + create_vlan_tag(vlan_src) + data[12:]
            send_to_link(out_interface, length + 4, tagged_frame)
        else: # acces -> acces
            if int(vlan_dest) == vlan_src:
                send_to_link(out_interface, length, data)

    else:
        if vlan_dest == "T": # trunk -> trunk
            send_to_link(out_interface, length, data)
        else:
            if int(vlan_dest) == vlan_src: # trunk -> acces
                removed_tagged_frame = data[0:12] + data[16:]
                send_to_link(out_interface, length - 4, removed_tagged_frame)

# FUnction to check if the MAC address is multicast
def is_multicast(mac_addr: str) -> bool:

    braodcast_mac = "ff:ff:ff:ff:ff:ff"

    octet = int(mac_addr.split(":")[0], 16)
    return (octet & 1) != 0 and mac_addr.lower() != braodcast_mac


def bdpu_verif(bdpu_pack: BPDU, interface, dest_mac, data, len) -> bool:
    # Check for BPDU-specific multicast MAC address
    if is_multicast(dest_mac):
        bdpu_pack.process_bdpu_packet(interface, data, len)
        return True
    return False


def init_vlan_src(vlan_id, VLANS_map, interface) -> int:
    vlan_src:int = -1
    if vlan_id == -1:
        vlan_src = int(VLANS_map[get_interface_name(interface)])
    else:
        vlan_src = vlan_id

    return vlan_src


def verif_in_mac_table(mac_table, src_mac, interface, vlan_src):
    if src_mac not in mac_table:
        mac_table[src_mac] = (interface, vlan_src)

    return mac_table


def main():
    switch_id = sys.argv[1]
    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    print(f"# Starting switch with id {switch_id}", flush=True)
    print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))
    
    # Read the priority and the VLANs
    priority, VLANS_map = read_config_file(switch_id, interfaces)

    # Create the BPDU packet
    bdpu_packet = BPDU(priority, VLANS_map, interfaces)

    # Create a thread to send the BPDU packet every second
    t = threading.Thread(target=send_bdpu_every_sec, args=(bdpu_packet, interfaces))

    t.start()


    for i in interfaces:
        print(get_interface_name(i))

    mac_table = {}

    while True:
        interface, data, length = recv_from_any_link()

        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)

        # Human-readable MAC addresses
        dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac = ':'.join(f'{b:02x}' for b in src_mac)

        print(f'Destination MAC: {dest_mac}')
        print(f'Source MAC: {src_mac}')
        print(f'EtherType: {ethertype}')
        print(f'VLAN ID: {vlan_id}')
        print(f"Received frame of size {length} on interface {interface}", flush=True)

        # Check for BPDU frames
        if bdpu_verif(bdpu_packet, interface, dest_mac, data, length):
            continue

        vlan_src:int = init_vlan_src(vlan_id, VLANS_map, interface)

        # Learn source MAC address with VLAN awareness
        mac_table = verif_in_mac_table(mac_table, src_mac, interface, vlan_src)

        if is_unicast(dest_mac):
            # Check destination in MAC table and match VLAN ID
            if dest_mac in mac_table:
                out_interface = mac_table[dest_mac][0]
                
                #Just sent te packet to the right interface
                vlan_dest = VLANS_map[get_interface_name(out_interface)]
                send_with_vlan(vlan_id, vlan_src, vlan_dest, out_interface, length, data)
            else:
                # Flood frame on all matching VLAN interfaces except incoming
                for i in bdpu_packet.interfaces_that_work():
                    if i != interface:
                        vlan_dest = VLANS_map[get_interface_name(i)]
                        send_with_vlan(vlan_id, vlan_src, vlan_dest, i, length, data)
        else:
            # Broadcast frame to all matching VLAN interfaces
            for i in bdpu_packet.interfaces_that_work():
                if i != interface:
                    vlan_dest = VLANS_map[get_interface_name(i)]
                    send_with_vlan(vlan_id, vlan_src ,vlan_dest, i, length, data)

if __name__ == "__main__":
    main()
