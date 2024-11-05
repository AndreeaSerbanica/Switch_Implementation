# Switch Imeplementation

## About Code


**Task 1 - MAC Table:**

The switch has a MAC Table, which is initially an empty dictionary `mac_table`. 
Over time, the switch populates this table with information about the routes for sending data.

The switch updates the `mac_table` with the source MAC address (`verif_in_mac_table()`)

If the switch cannot locate the destination address in the MAC Table, it broadcasts the frame to all interfaces, except the one it was received on. Otherwise, it forwards the frame directly to the destination.
```pyhton
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
```

**Task 2 - VLAN:**

The switch needs to check the VLAN to send frames more efficiently, limiting transmission to specific ports only.

The switch reads port priorities and VLAN assignments from the configuration file using(`read_config_file()`). The VLANs are stored in a dictionary called `VLANS_map`.

The information is send through the `send_with_vlan()` function, which has **4 cases**: 
- **access to trunk:** Sends a tagged frame.
- **access to access:** Sends the frame without modification.
- **trunk to trunk:** Forwards the frame as-is.
- **trunk to access:** Sends an untagged frame.

**Task 3 - STP:**




## Running

```bash
sudo python3 checker/topo.py
```

This will open 9 terminals, 6 hosts and 3 for the switches. On the switch terminal you will run 

```bash
make run_switch SWITCH_ID=X # X is 0,1 or 2
```

The hosts have the following IP addresses.
```
host0 192.168.1.1
host1 192.168.1.2
host2 192.168.1.3
host3 192.168.1.4
host4 192.168.1.5
host5 192.168.1.6
```

We will be testing using the ICMP. For example, from host0 we will run:

```
ping 192.168.1.2
```

Note: We will use wireshark for debugging. From any terminal you can run `wireshark&`.
