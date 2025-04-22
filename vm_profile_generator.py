import random
import numpy as np
import os
from ProteanData.Sampler import ProteanSampler

def load_trace_data(trace_dir, num_traces, time_steps=288):
    """
    Load trace data from the PlanetLab directory.
    """
    trace_files = [f for f in os.listdir(trace_dir) if os.path.isfile(os.path.join(trace_dir, f))]
    selected_traces = random.sample(trace_files, num_traces)
    trace_data = {}

    for i, filename in enumerate(selected_traces):
        path = os.path.join(trace_dir, filename)
        with open(path, 'r') as f:
            values = [float(line.strip()) for line in f if line.strip().isdigit()]
        values = values[:time_steps]
        if len(values) < time_steps:
            raise ValueError(f"Trace file {filename} has fewer than {time_steps} entries.")
        trace_data[i] = [min(max(v / 100.0, 0.0), 1.0) for v in values]

    return trace_data

def generate_initial_vm_profiles(
    num_vms,
    trace_dir,
    long_lived_ratio=1.0,
    long_lived_duration=1e9,
    time_steps=288
):
    """
    Generate a group of VMs that all exist at time = 0.

    :param num_vms: Total number of VMs to generate
    :param trace_dir: Directory containing PlanetLab trace files
    :param long_lived_ratio: Fraction of VMs that are long-lived (e.g., 0.3 for 30%)
    :param long_lived_duration: Duration (in steps) to assign to long-lived VMs
    :param time_steps: Number of simulation steps
    :return: List of VM profile dicts
    """
    trace_data = load_trace_data(trace_dir, num_traces=num_vms, time_steps=time_steps)
    protean = ProteanSampler()
    vm_profiles = []

    num_long_lived_vms = int(num_vms * long_lived_ratio)
    num_short_lived_vms = num_vms - num_long_lived_vms

    short_lived_lifetimes = protean.VM_lifetime(num_short_lived_vms)

    for vm_index in range(num_vms):
        trace_index = vm_index % len(trace_data)
        is_long_lived = vm_index < num_long_lived_vms
        lifetime = long_lived_duration if is_long_lived else int(np.ceil(short_lived_lifetimes[vm_index - num_long_lived_vms] / 5)) # In Time Steps

        vm_profiles.append({
            "vm_id": vm_index,
            "arrival_time": 0,
            "lifetime": lifetime,
            "cpu_utilization": trace_data[trace_index][:time_steps],
        })

    return vm_profiles

def generate_dynamic_vm_profiles(
    trace_dir,
    num_hosts,
    num_peak_arrive,
    initial_vm_id=0,
    time_steps=288
):
    """
    Generate all VM profiles for dynamic arrivals using PlanetLab traces and Protean arrival/lifetime model.

    Each VM profile includes:
    - vm_id
    - arrival_time (step)
    - lifetime (steps)
    - cpu_utilization (list of length time_steps)

    :param trace_dir: Directory for trace data
    :param num_hosts: Number of physical hosts (controls how many traces to load)
    :param num_peak_arrive: Scaling factor for Protean arrivals
    :param initial_vm_id: Starting vm_id for dynamic VMs (to avoid id overlap)
    :param time_steps: Total number of simulation steps
    :return: List of VM profile dicts
    """
    protean = ProteanSampler()
    arrival_rates = protean.VM_arrival_rates(scale=num_peak_arrive)
    trace_data = load_trace_data(trace_dir, num_traces=num_hosts * 4, time_steps=time_steps)

    vm_profiles = []
    vm_id = initial_vm_id

    for t, num_arrivals in enumerate(arrival_rates):
        num_arrivals = int(num_arrivals)
        if num_arrivals == 0:
            continue
        lifetimes = protean.VM_lifetime(num_arrivals)
        for i in range(num_arrivals):
            trace_index = vm_id % len(trace_data)
            lifetime = int(np.ceil(lifetimes[i] / 5))

            while lifetime > time_steps:
                lifetime = int(np.ceil(protean.VM_lifetime(1)[0] / 5))

            profile = {
                "vm_id": vm_id,
                "arrival_time": t,
                "lifetime": lifetime,
                "cpu_utilization": trace_data[trace_index][:time_steps]
            }
            vm_profiles.append(profile)
            vm_id += 1

    return vm_profiles