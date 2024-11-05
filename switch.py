#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name
<<<<<<< HEAD
from stp import BPDU, create_bpdu_tag # type: ignore
=======
from stp import BPDU, create_bpdu # type: ignore
>>>>>>> 2ba22e4b4ba98b28bfd5e031f1bd9ebafc0c67ca

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
<<<<<<< HEAD
                    # print(f"Sending BPDU on interface {i} - {get_interface_name(i)}")
                    bpdu_data = create_bpdu_tag(bdpu_pack.root_bridge_ID, bdpu_pack.own_bridge_ID, 0)
=======
                    print(f"Sending BPDU on interface {i} - {get_interface_name(i)}")
                    bpdu_data = create_bpdu(bdpu_pack.root_bridge_ID, bdpu_pack.own_bridge_ID, 0)
>>>>>>> 2ba22e4b4ba98b28bfd5e031f1bd9ebafc0c67ca
                    send_to_link(i, len(bpdu_data), bpdu_data)

        time.sleep(1)



def is_unicast(mac):
    first_byte = int(mac[:2], 16)
<<<<<<< HEAD
    return (first_byte & 1) == 0


def read_config_file(switch_id, interfaces):

    vlans_config = {}
    config_file = f"configs/switch{switch_id}.cfg"

    f_in = open(config_file, "r")
    priority = int(f_in.readline())

=======
    return (first_byte & 1) == 0 and not  is_multicast(mac)


def read_config_file(switch_id, interfaces):
    f_in = open(f"configs/switch{switch_id}.cfg", "r")
    priority = int(f_in.readline())

    vlans_config = {}
>>>>>>> 2ba22e4b4ba98b28bfd5e031f1bd9ebafc0c67ca
    for _ in interfaces:
        config = f_in.readline().rstrip("\n").split(" ")
        vlans_config[config[0]] = config[1]

    f_in.close()

    return priority, vlans_config


def send_with_vlan(vlan_id, vlan_src, vlan_dest, out_interface, length, data):

    # if the switch recieve from a acces port and sent to a trunk port
    if vlan_id == -1:
<<<<<<< HEAD
        # print(f"I came from an acces port")
=======
        print(f"I came from an acces port")
>>>>>>> 2ba22e4b4ba98b28bfd5e031f1bd9ebafc0c67ca
        vlan_id = vlan_src
        if vlan_dest == "T":
            tagged_frame = data[0:12] + create_vlan_tag(vlan_src) + data[12:]
            send_to_link(out_interface, length + 4, tagged_frame)
<<<<<<< HEAD
            # print(f"Forwarding frame to interface {out_interface} with VLAN {vlan_dest}")
        else:
            if int(vlan_dest) == vlan_src:
                send_to_link(out_interface, length, data)
                # print(f"Forwarding frame to interface {out_interface} with VLAN {vlan_dest}")
            # else:
            #     print(f"Dropping frame due to VLAN mismatch (frame VLAN: {vlan_id}, port VLAN: {vlan_dest})")

    else:
        # print(f"I came from an trunk port")

        if vlan_dest == "T":
            send_to_link(out_interface, length, data)
            # print(f"Forwarding tagged frame to trunk interface {out_interface} with VLAN {vlan_id}")
=======
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
>>>>>>> 2ba22e4b4ba98b28bfd5e031f1bd9ebafc0c67ca
        else:
            if int(vlan_dest) == vlan_src:
                removed_tagged_frame = data[0:12] + data[16:]
                send_to_link(out_interface, length - 4, removed_tagged_frame)
<<<<<<< HEAD
                # print(f"Forwarding frame to interface {out_interface} with VLAN {vlan_dest}")
            # else:
            #     print(f"Dropping frame due to VLAN mismatch (frame VLAN: {vlan_id}, port VLAN: {vlan_dest})")


def is_multicast(mac_addr: str) -> bool:

    braodcast_mac = "ff:ff:ff:ff:ff:ff"

    octet = int(mac_addr.split(":")[0], 16)
    return (octet & 1) != 0 and mac_addr.lower() != braodcast_mac
=======
                print(f"Forwarding frame to interface {out_interface} with VLAN {vlan_dest}")
            else:
                print(f"Dropping frame due to VLAN mismatch (frame VLAN: {vlan_id}, port VLAN: {vlan_dest})")


def is_multicast(mac: str) -> bool:
    octet = int(mac.split(":")[0], 16)
    return (octet & 1) != 0 and mac.lower() != "ff:ff:ff:ff:ff:ff"
>>>>>>> 2ba22e4b4ba98b28bfd5e031f1bd9ebafc0c67ca


def is_bpdu(bdpu_pack: BPDU, interface, dest_mac, data, len) -> bool:
    # Check for BPDU-specific multicast MAC address
    if is_multicast(dest_mac):
<<<<<<< HEAD
=======
        print(f"I am an Bdpu pack")
>>>>>>> 2ba22e4b4ba98b28bfd5e031f1bd9ebafc0c67ca
        bdpu_pack.process_bdpu_packet(interface, data, len)
        return True
    return False


<<<<<<< HEAD
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
        # print(f"Learning MAC {src_mac} on interface {interface} with VLAN {vlan_src}")

    return mac_table

=======
>>>>>>> 2ba22e4b4ba98b28bfd5e031f1bd9ebafc0c67ca

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
    
<<<<<<< HEAD
    # print(f"Priority: {priority}")
    # print(f"VLANS map: {VLANS_map}")
=======
    print(f"Priority: {priority}")
    print(f"VLANS map: {VLANS_map}")
>>>>>>> 2ba22e4b4ba98b28bfd5e031f1bd9ebafc0c67ca
    

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

<<<<<<< HEAD
        vlan_src:int = init_vlan_src(vlan_id, VLANS_map, interface)

        # Learn source MAC address with VLAN awareness
        mac_table = verif_in_mac_table(mac_table, src_mac, interface, vlan_src)
=======
        vlan_src:int = -1
        if vlan_id == -1:
            vlan_src = int(VLANS_map[get_interface_name(interface)])
        else:
            vlan_src = vlan_id

        # Learn source MAC address with VLAN awareness
        if src_mac not in mac_table:
            mac_table[src_mac] = (interface, vlan_src)
            print(f"Learning MAC {src_mac} on interface {interface} with VLAN {vlan_src}")

        # # Check for BPDU frames
        # print(f"verif bdpu")
        # if is_bpdu(bdpu_packet, interface, dest_mac, data, length):
        #     continue

>>>>>>> 2ba22e4b4ba98b28bfd5e031f1bd9ebafc0c67ca

        if is_unicast(dest_mac):
            # Check destination in MAC table and match VLAN ID
            if dest_mac in mac_table:
                out_interface = mac_table[dest_mac][0]
                
                # Filter by VLAN ID
<<<<<<< HEAD
                # print(f"Just sending")
=======
                print(f"Just sending")
>>>>>>> 2ba22e4b4ba98b28bfd5e031f1bd9ebafc0c67ca
                vlan_dest = VLANS_map[get_interface_name(out_interface)]
                send_with_vlan(vlan_id, vlan_src, vlan_dest, out_interface, length, data)
            else:
                # Flood frame on all matching VLAN interfaces except incoming
<<<<<<< HEAD
                # print(f"Making flooding")
=======
                print(f"Making flooding")
>>>>>>> 2ba22e4b4ba98b28bfd5e031f1bd9ebafc0c67ca
                for i in bdpu_packet.interfaces_that_work():
                    if i != interface:
                        vlan_dest = VLANS_map[get_interface_name(i)]
                        send_with_vlan(vlan_id, vlan_src, vlan_dest, i, length, data)
        else:
            # Broadcast frame to all matching VLAN interfaces
<<<<<<< HEAD
            # print(f"Making broadcast")
=======
            print(f"Making broadcast")
>>>>>>> 2ba22e4b4ba98b28bfd5e031f1bd9ebafc0c67ca
            for i in bdpu_packet.interfaces_that_work():
                if i != interface:
                    vlan_dest = VLANS_map[get_interface_name(i)]
                    send_with_vlan(vlan_id, vlan_src ,vlan_dest, i, length, data)

        # TODO: Implement STP support

if __name__ == "__main__":
    main()
