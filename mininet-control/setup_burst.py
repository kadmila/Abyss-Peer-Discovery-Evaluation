#!/usr/bin/env python3
# ------------------------------------------------------------------
# Global-Scale WAN Simulation Setup
# Creates a fully-connected mesh of city routers with realistic latencies
# ------------------------------------------------------------------

import os
import sys
import json
import math
import random
import argparse
import time

# Add mininet to path
module_path = os.path.abspath('../mininet')
if module_path not in sys.path:
    sys.path.append(module_path)

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.node import OVSBridge


# ------------------------------------------------------------------
# Argument Parsing
# ------------------------------------------------------------------

parser = argparse.ArgumentParser(
    description='Global WAN Simulation with RIPE Atlas data'
)
parser.add_argument(
    '--n_peers',
    type=int,
    default=100,
    help='Number of peers to generate (default: 100)'
)
parser.add_argument(
    '--n_churn',
    type=int,
    default=10,
    help='Number of peers to churn (default: 10)'
)
parser.add_argument(
    '--seed',
    type=int,
    default=None,
    help='Random seed for peer placement (default: None)'
)
args = parser.parse_args()

# Initialize random seed if provided
if args.seed is not None:
    random.seed(args.seed)
    print(f'Random seed set to: {args.seed}')


# ------------------------------------------------------------------
# Global Configuration
# ------------------------------------------------------------------

CONFIG_PATH = './city_config.json'

def load_city_config():
    """Load and return city configuration from JSON file."""
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        print(f'Loaded configuration for {len(config)} cities from {CONFIG_PATH}')
        return config
    except FileNotFoundError:
        print(f'Error: Configuration file not found: {CONFIG_PATH}')
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f'Error: Invalid JSON in {CONFIG_PATH}: {e}')
        sys.exit(1)

def preprocess_city_links(city_config):
    """
    Pre-process all city pairs and assign incremental link IDs.
    This ensures deterministic, collision-free link IDs for IP addressing.
    
    Args:
        city_config: Dictionary of city configurations
        
    Returns:
        Dictionary mapping (city1, city2) tuples to link IDs (1-based)
    """
    link_id_map = {}
    cities = list(city_config.keys())
    link_id = 1
    
    for i, city1 in enumerate(cities):
        for city2 in cities[i + 1:]:
            # Store both orderings for easy lookup
            link_id_map[(city1, city2)] = link_id
            link_id_map[(city2, city1)] = link_id
            link_id += 1
    
    print(f'Pre-processed {link_id - 1} city-to-city links with incremental IDs (1-{link_id - 1})')
    return link_id_map


# Parse configuration once at module level
CITY_CONFIG = load_city_config()
CITY_ABBRS = list(CITY_CONFIG.keys())  # List of city abbreviations
CITY_NAMES = {abbr: data['city'] for abbr, data in CITY_CONFIG.items()}  # Map abbr -> full city name
CITY_NUMBERS = {abbr: idx + 1 for idx, abbr in enumerate(CITY_ABBRS)}  # Map abbr -> city number (1-based)
LINK_ID_MAP = preprocess_city_links(CITY_CONFIG)


def generate_peer_placements(n):
    """
    Generate N peer placements by selecting cities and distances.
    
    Cities are selected with probability proportional to population.
    Distances are selected uniformly in 2D space within each city's circular area.
    
    Args:
        n: Number of peers to generate
        
    Returns:
        List of tuples (city_abbr: str, distance: float)
    """
    populations = [CITY_CONFIG[city]['population'] for city in CITY_ABBRS]
    total_population = sum(populations)
    
    # Calculate probability weights for each city
    weights = [pop / total_population for pop in populations]
    
    placements = []
    for _ in range(n):
        # Select city with probability proportional to population
        city_abbr = random.choices(CITY_ABBRS, weights=weights, k=1)[0]
        
        # Select distance uniformly in 2D circular area
        # For uniform distribution in a circle, distance ~ sqrt(uniform(0,1)) * radius
        city_radius = CITY_CONFIG[city_abbr]['radius']
        distance = math.sqrt(random.random()) * city_radius
        
        placements.append((city_abbr, distance))
    
    return placements

PEER_CONFIG = generate_peer_placements(args.n_peers)

REFRACTION_COEFFICIENT = 1.5
DISTANCE_MULTIPLIER = 1.5
def distance_to_delay(dist_km:float) -> float :
    return (dist_km * DISTANCE_MULTIPLIER) / (299_792.458 / REFRACTION_COEFFICIENT) * 1000

# ------------------------------------------------------------------
# Topology Class
# ------------------------------------------------------------------

class GlobalWANTopo(Topo):
    """
    Global WAN topology with 19 cities.
    Each city has a router (host with IP forwarding), fully connected with realistic latencies.
    """

    def build(self):
        """Build the topology with city routers and inter-city links."""
        
        # Use the pre-loaded global configuration
        city_config = CITY_CONFIG
        
        # Store link metadata for routing configuration
        self.links_info = []
        
        # Create a router and switch for each city
        print("Creating city routers and switches...")
        for city_abbr in CITY_ABBRS:
            # Add host node that will act as a router
            # IP addresses will be configured later in configure_routers()
            self.addHost(f'r_{city_abbr}', ip=None)
            
            # Add switch for this city 
            self.addSwitch(f's_{city_abbr}', cls=OVSBridge, dpid=f"{1000 + CITY_NUMBERS[city_abbr]:016x}")
            
            # Connect router to switch with named interface
            self.addLink(
                f'r_{city_abbr}',
                f's_{city_abbr}',
                intfName1=f'r_{city_abbr}-s',
                intfName2=f's_{city_abbr}-r'
            )
        
        # Create fully-connected mesh between all city routers
        print("\nCreating inter-city links...")
        link_count = 0
        
        for i, city1 in enumerate(CITY_ABBRS):
            for city2 in CITY_ABBRS[i + 1:]:
                # Get network statistics from city1 to city2
                stats = city_config[city1]['network_stats'][city2]
                mean_rtt = stats['mean']
                stddev_rtt = stats['stddev']
                
                # Calculate one-way delay (RTT / 2)
                delay_ms = mean_rtt / 2.0
                
                # Add jitter based on standard deviation
                # Use stddev as jitter to simulate variance
                jitter_ms = stddev_rtt / 2.0
                
                # Get pre-assigned incremental link ID
                link_id = LINK_ID_MAP[(city1, city2)]
                
                # Create link with named interfaces for explicit routing
                self.addLink(
                    f'r_{city1}',
                    f'r_{city2}',
                    intfName1=f'r_{city1}-{city2}',
                    intfName2=f'r_{city2}-{city1}',
                    cls=TCLink,
                    delay=f'{delay_ms:.2f}ms',
                    jitter=f'{jitter_ms:.2f}ms'
                )
                
                # Store link metadata for routing configuration
                self.links_info.append({
                    'city1': city1,
                    'city2': city2,
                    'link_id': link_id,
                    'intf1': f'r_{city1}-{city2}',
                    'intf2': f'r_{city2}-{city1}',
                    'delay_ms': delay_ms,
                    'jitter_ms': jitter_ms
                })
                
                link_count += 1
                # print(f'  Link {link_count}: {city1} <-> {city2} '
                #       f'(delay: {delay_ms:.2f}ms ± {jitter_ms:.2f}ms, link_id: {link_id})')
        
        print(f'\nTopology built: {len(CITY_ABBRS)} routers, {len(CITY_ABBRS)} switches, {link_count} inter-city links')

        # ----------------------------------------------------------
        # Peer Placement
        # ----------------------------------------------------------
        
        # Store peer metadata for configuration
        self.peers_info = []
        
        if len(PEER_CONFIG) > 0:
            print(f"\nCreating {len(PEER_CONFIG)} peer hosts...")
            
            for peer_idx, (city_abbr, distance) in enumerate(PEER_CONFIG):
                peer_number = peer_idx + 1
                
                # Calculate IP address: 20.{city_number}.{hi}.{lo}
                city_number = CITY_NUMBERS[city_abbr]
                hi_byte = (peer_number // 250) + 1  # High byte
                lo_byte = (peer_number % 250) + 1  # Low byte
                peer_ip = f'20.{city_number}.{hi_byte}.{lo_byte}'
                gateway_ip = f'20.{city_number}.1.1'
                
                # Add peer host with IP address
                peer = self.addHost(
                    f'h{peer_number}',
                    ip=f'{peer_ip}/16',
                    defaultRoute=f'via {gateway_ip}'
                )

                delay_ms = distance_to_delay(distance)
                
                # Connect peer to city switch
                self.addLink(
                    f'h{peer_number}',
                    f's_{city_abbr}',
                    intfName1=f'h_eth1',
                    intfName2=f's_{city_abbr}-h{peer_number}',
                    cls=TCLink,
                    delay=f'{delay_ms:.2f}ms'
                )
                
                # Store peer metadata
                self.peers_info.append({
                    'peer_name': f'h{peer_number}',
                    'peer_number': peer_number,
                    'city_abbr': city_abbr,
                    'city_number': city_number,
                    'delay_ms': delay_ms,
                    'ip': peer_ip,
                    'gateway': gateway_ip
                })

                #print(f'  Peer {peer_number}: {CITY_NAMES[city_abbr]} delay: {delay_ms:.2f} ms, IP: {peer_ip}')
            
            print(f'  Created {len(PEER_CONFIG)} peers across {len(set(p[0] for p in PEER_CONFIG))} cities')

# ------------------------------------------------------------------
# Network Setup and Configuration
# ------------------------------------------------------------------

def router_internal_config(router, city_abbr):
    """
    Configure router internal settings including IP forwarding and switch interface.
    
    Args:
        router: Mininet router node
        city_abbr: City abbreviation for this router
    """
    # Enable IP forwarding
    router.cmd('sysctl -w net.ipv4.ip_forward=1 > /dev/null')
    
    # Configure router-switch interface with peer network IP
    # Peer network: 20.{city_number}.0.0/16
    # Router gets 20.{city_number}.0.1/16 as gateway
    city_number = CITY_NUMBERS[city_abbr]
    router_to_switch_intf = f'r_{city_abbr}-s'
    router_to_switch_ip = f'20.{city_number}.1.1'
    router_inbound_range = f'20.{city_number}.0.0/16'
    
    # Assign IP address to switch interface
    router.cmd(f'ifconfig {router_to_switch_intf} {router_to_switch_ip} netmask 255.255.0.0')
    router.cmd(f'ip route add {router_inbound_range} dev {router_to_switch_intf}')

def configure_routers(net, topo):
    """
    Configure routers with IP addresses, enable IP forwarding, and set up routing tables.
    
    Args:
        net: Mininet network instance
        topo: GlobalWANTopo instance with links_info
    """
    print("\nConfiguring routers...")
    
    # Track which routers we've already configured IP forwarding for
    routers_configured = set()
    
    print("  Configuring links (IP forwarding, IP addresses, and routes)...")
    
    # Single iteration over all links
    for link_info in topo.links_info:
        city1 = link_info['city1']
        city2 = link_info['city2']
        link_id = link_info['link_id']
        intf1 = link_info['intf1']
        intf2 = link_info['intf2']
        
        # Get routers
        router1 = net.get(f'r_{city1}')
        router2 = net.get(f'r_{city2}')
        
        # Configure router internal settings (only once per router)
        if city1 not in routers_configured:
            router_internal_config(router1, city1)
            routers_configured.add(city1)
        
        if city2 not in routers_configured:
            router_internal_config(router2, city2)
            routers_configured.add(city2)
        
        # Assign IP addresses to point-to-point interfaces
        # Point-to-point /30 subnet: 10.{link_id}.0.{1,2}/30
        ip1 = f'10.{link_id}.0.1'
        ip2 = f'10.{link_id}.0.2'

        subnet_mask = f'255.255.255.3/30'
        
        router1.cmd(f'ifconfig {intf1} {ip1} netmask {subnet_mask}')
        router2.cmd(f'ifconfig {intf2} {ip2} netmask {subnet_mask}')
        
        # Add routes: each router adds a route to reach the other router's IP
        router1.cmd(f'ip route add {ip2} dev {intf1}')
        router2.cmd(f'ip route add {ip1} dev {intf2}')

        # Add routes: route peer traffic via the other router
        city1_number = CITY_NUMBERS[city1]
        city2_number = CITY_NUMBERS[city2]
        peer_network1 = f'20.{city1_number}.0.0/16'
        peer_network2 = f'20.{city2_number}.0.0/16'
        router1.cmd(f'ip route add {peer_network2} via {ip2} dev {intf1}')
        router2.cmd(f'ip route add {peer_network1} via {ip1} dev {intf2}')
        
        # print(f'    Link {link_id}: {city1} ({ip1}) <-> {city2} ({ip2})')
    
    print(f'\n  Configuration complete: {len(routers_configured)} routers, {len(topo.links_info)} links')

# ------------------------------------------------------------------
# Application Configuration
# ------------------------------------------------------------------

def gen_scenario_scale(net, topo) -> int:
    """
    Generate scenario files for each peer.
    Creates files h1 to h{n_peers} in ./tmp/scenario directory.
    Each file contains a JSON array.
    """
    scenario_dir = './tmp/scenario'
    peer_names = [peer_info['peer_name'] for peer_info in topo.peers_info]

    time_now = 0
    scenario_data = {peer_name: [] for peer_name in peer_names}

    # initial world
    scenario_data['h1'].append({
        'time': f'{time_now}',
        'do': 'open',
    })

    # initial 10: prepare for dial
    for i in range(2, 101):
        scenario_data['h1'].append({
            'time': f'{time_now}',
            'do': 'add',
            'id': f'h{i}',
        })
    for i in range(2, 101):
        scenario_data[f'h{i}'].append({
            'time': f'{time_now}',
            'do': 'add',
            'id': 'h1',
        })

    # initial 10: join to first one.
    time_now += 1
    for i in range(2, 101):
        scenario_data[f'h{i}'].append({
            'time': f'{time_now}',
            'do': 'dial',
            'id': 'h1',
        })

    time_now += 1
    for i in range(2, 101):
        scenario_data[f'h{i}'].append({
            'time': f'{time_now}',
            'do': 'join',
            'id': 'h1',
        })

    peers_in_world = set()
    for i in range(1, 101):
        peers_in_world.add(f'h{i}')

    time_now += 60
    
    # followings: join to peers in the world, leave.
    for cycle in range((args.n_peers - 100) // args.n_churn):
        time_now += 8 # 10 second gap for stabilization

        # (joiner id, target id)[args.n_churn]
        leave_targets_ids = random.sample(sorted(peers_in_world), args.n_churn)
        for leave_target_id in leave_targets_ids:
            peers_in_world.remove(leave_target_id)

        join_targets_ids = [(f'h{100 + args.n_churn * cycle + i}', f'{random.sample(sorted(peers_in_world), 1)[0]}') for i in range(1, args.n_churn +1)]
        for joiner_id, target_id in join_targets_ids:
            scenario_data[target_id].append({
                'time': f'{time_now}',
                'do': 'add',
                'id': joiner_id
            })
            scenario_data[joiner_id].append({
                'time': f'{time_now}',
                'do': 'add',
                'id': target_id
            })

        time_now += 1

        for joiner_id, target_id in join_targets_ids:
            scenario_data[target_id].append({
                'time': f'{time_now}',
                'do': 'dial',
                'id': joiner_id
            })
            scenario_data[joiner_id].append({
                'time': f'{time_now}',
                'do': 'dial',
                'id': target_id
            })

        time_now += 1
        
        for joiner_id, target_id in join_targets_ids:
            scenario_data[joiner_id].append({
                'time': f'{time_now}',
                'do': 'join',
                'id': target_id,
            })

        for leave_target_id in leave_targets_ids:
            scenario_data[leave_target_id].append({
                'time': f'{time_now}',
                'do': 'close',
                'id': leave_target_id
            })
            
        for joiner_id, _ in join_targets_ids:
            peers_in_world.add(joiner_id)
    
    for peer_name in peer_names:
        file_path = os.path.join(scenario_dir, peer_name)
        
        with open(file_path, 'w') as f:
            json.dump(scenario_data[peer_name], f)

    time_now += 30
    return time_now

def run_peer_applications(net, topo) -> int:
    peers = [(net.get(peer_info['peer_name']), peer_info['peer_name']) for peer_info in topo.peers_info]
    results_path = f'./results/{args.n_peers}/{args.seed}'
    scenario_dir = './tmp/scenario'
    contact_dir = './tmp/contact'

    print("Generating scenario...")
    scenario_duration = gen_scenario_scale(net, topo)

    print("Starting ifstat...")
    for peer, peer_name in peers:
        peer.cmd(f'ifstat -i h_eth1 -n 0.1 > {results_path}/ifstat_{peer_name}.log &')
        
    time_start_ms = int(time.time() * 1000) + 10_000
    print("Starting application...")
    for peer, peer_name in peers:
        peer.cmd(f'./abyss_test/scenario_run --id={peer_name} --contact_dir={contact_dir} --t_start={time_start_ms} --duration={scenario_duration} --scenario={scenario_dir}/{peer_name} --out {results_path}/evnt_{peer_name}.log  &> {results_path}/out_{peer_name}.log &')
    
    return scenario_duration

def stop_peer_applications(net, topo):
    peer_names = [peer_info['peer_name'] for peer_info in topo.peers_info]
    for peer_name in peer_names:
        peer = net.get(peer_name)
        peer.cmd('pkill ifstat')
    
    for peer_name in peer_names:
        peer = net.get(peer_name)
        peer.cmd('wait')

def run_simulation():
    """Main function to set up and run the simulation."""
    
    # Set log level
    setLogLevel('output')
    
    # Create topology
    print("\nBuilding topology...")
    topo = GlobalWANTopo()
    
    # Create network with TC link support for delay/bandwidth
    print("\nStarting network...")
    net = Mininet(
        topo=topo,
        link=TCLink,
        controller=None,
        autoSetMacs=True,
        autoStaticArp=True
    )
    
    # Configure routers (IP addresses, forwarding, routing tables)
    configure_routers(net, topo)
    
    # Start network
    net.start()
    time.sleep(3)

    print("\nRunning peer applications...")
    scenario_duration = run_peer_applications(net, topo)
    print("Peer applications started.")
        
    # Start CLI
    #CLI(net)
    
    time.sleep(scenario_duration + 12)

    print("\nStopping peer applications...")
    stop_peer_applications(net, topo)
    print("Peer applications stopped.")
    
    # Cleanup
    print("\nStopping network...")
    net.stop()
    print("Done.")


# ------------------------------------------------------------------
# Main Execution
# ------------------------------------------------------------------

try:
    run_simulation()
except KeyboardInterrupt:
    print("\n\nInterrupted by user")
    sys.exit(0)
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
