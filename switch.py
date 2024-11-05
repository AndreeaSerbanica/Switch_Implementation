#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name
from stp import BPDU, create_bpdu # type: ignore

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
                    # print(f"Sending BPDU on interface {i} - {get_interface_name(i)}")
                    bpdu_data = create_bpdu(bdpu_pack.root_bridge_ID, bdpu_pack.own_bridge_ID, 0)
                    send_to_link(i, len(bpdu_data), bpdu_data)

        time.sleep(1)



def is_unicast(mac):
    first_byte = int(mac[:2], 16)
    return (first_byte & 1) == 0


def read_config_file(switch_id, interfaces):
    f_in = open(f"configs/switch{switch_id}.cfg", "r")
    priority = int(f_in.readline())

    vlans_config = {}
    for _ in interfaces:
        config = f_in.readline().rstrip("\n").split(" ")
        vlans_config[config[0]] = config[1]

    f_in.close()

    return priority, vlans_config


def send_with_vlan(vlan_id, vlan_src, vlan_dest, out_interface, length, data):

    # if the switch recieve from a acces port and sent to a trunk port
    if vlan_id == -1:
        print(f"I came from an acces port")
        vlan_id = vlan_src
        if vlan_dest == "T":
            tagged_frame = data[0:12] + create_vlan_tag(vlan_src) + data[12:]
            send_to_link(out_interface, length + 4, tagged_frame)
            print(f"Forwarding frame to interface {out_interface} with VLAN {vlan_dest}")
        else:
            if int(vlan_dest) == vlan_src:
                send_to_link(out_interface, length, data)
                print(f"Forwarding frame to interface {out_interface} with VLAN {vlan_dest}")
            else:
                print(f"Dropping frame due to VLAN mismatch (frame VLAN: {vlan_id}, port VLAN: {vlan_dest})")

    else:
        print(f"I came from an trunk port")

        if vlan_dest == "T":
            send_to_link(out_interface, length, data)
            print(f"Forwarding tagged frame to trunk interface {out_interface} with VLAN {vlan_id}")
        else:
            if int(vlan_dest) == vlan_src:
                removed_tagged_frame = data[0:12] + data[16:]
                send_to_link(out_interface, length - 4, removed_tagged_frame)
                print(f"Forwarding frame to interface {out_interface} with VLAN {vlan_dest}")
            else:
                print(f"Dropping frame due to VLAN mismatch (frame VLAN: {vlan_id}, port VLAN: {vlan_dest})")


def is_multicast(mac: str) -> bool:
    octet = int(mac.split(":")[0], 16)
    return (octet & 1) != 0 and mac.lower() != "ff:ff:ff:ff:ff:ff"


def is_bpdu(bdpu_pack: BPDU, interface, dest_mac, data, len) -> bool:
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
        print(f"Learning MAC {src_mac} on interface {interface} with VLAN {vlan_src}")

    return mac_table


def main():
    switch_id = sys.argv[1]
    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    print(f"# Starting switch with id {switch_id}", flush=True)
    print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))
    
    priority, VLANS_map = read_config_file(switch_id, interfaces)

    bdpu_packet = BPDU(priority, VLANS_map, interfaces)


    t = threading.Thread(target=send_bdpu_every_sec, args=(bdpu_packet, interfaces))

    t.start()


    for i in interfaces:
        print(get_interface_name(i))
    
    print(f"Priority: {priority}")
    print(f"VLANS map: {VLANS_map}")
    

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
        if is_bpdu(bdpu_packet, interface, dest_mac, data, length):
            continue

        vlan_src:int = init_vlan_src(vlan_id, VLANS_map, interface)

        # Learn source MAC address with VLAN awareness
        mac_table = verif_in_mac_table(mac_table, src_mac, interface, vlan_src)

        if is_unicast(dest_mac):
            # Check destination in MAC table and match VLAN ID
            if dest_mac in mac_table:
                out_interface = mac_table[dest_mac][0]
                
                # Filter by VLAN ID
                print(f"Just sending")
                vlan_dest = VLANS_map[get_interface_name(out_interface)]
                send_with_vlan(vlan_id, vlan_src, vlan_dest, out_interface, length, data)
            else:
                # Flood frame on all matching VLAN interfaces except incoming
                print(f"Making flooding")
                for i in bdpu_packet.interfaces_that_work():
                    if i != interface:
                        vlan_dest = VLANS_map[get_interface_name(i)]
                        send_with_vlan(vlan_id, vlan_src, vlan_dest, i, length, data)
        else:
            # Broadcast frame to all matching VLAN interfaces
            print(f"Making broadcast")
            for i in bdpu_packet.interfaces_that_work():
                if i != interface:
                    vlan_dest = VLANS_map[get_interface_name(i)]
                    send_with_vlan(vlan_id, vlan_src ,vlan_dest, i, length, data)

        # TODO: Implement STP support

if __name__ == "__main__":
    main()
