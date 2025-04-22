# Full integration of dynamic VM add/remove based on arrival rates and VM lifetimes
# This assumes `create_vm_list` accepts a `start_id` argument and all necessary imports and classes exist

import os
import random
import numpy as np
from datacenter import Cloudlet
from Helper import create_host_list, create_vm_list
from schedule import SchedulerVM
from ProteanData.Sampler import ProteanSampler
import matplotlib.pyplot as plt

# -----------------------------
# Simulation Setup
# -----------------------------
random.seed(42)
np.random.seed(42)

hosts = create_host_list(20)
num_initial_vms = 40
num_peak_arrive = 2

vms = create_vm_list(num_initial_vms)

trace_dir = "planetlab/20110303"
trace_files = [f for f in os.listdir(trace_dir) if os.path.isfile(os.path.join(trace_dir, f))]
selected_traces = random.sample(trace_files, num_initial_vms)
trace_data = {}

for i, filename in enumerate(selected_traces):
    path = os.path.join(trace_dir, filename)
    with open(path, 'r') as f:
        values = [float(line.strip()) for line in f if line.strip().isdigit()]
    values = values[:288]
    if len(values) < 288:
        raise ValueError(f"Trace file {filename} has fewer than 288 entries.")
    trace_data[i] = [min(max(v / 100.0, 0.0), 1.0) for v in values]

cloudlets = [Cloudlet(f"C{i+1}", length=1e10) for i in range(num_initial_vms)]
scheduler = SchedulerVM(hosts)

scheduler.set_policy("energy_aware")
for host in hosts:
    host.enable_dvfs(True)
    host.power_off()

vm_cl_pairs = sorted(zip(vms, cloudlets), key=lambda pair: pair[0].cpu, reverse=True)
for i, cloudlet in enumerate(cloudlets):
    trace = trace_data[i]
    cpu_ratio = sum(trace) / len(trace)
    cloudlet.set_cpu_demand_ratio(cpu_ratio, 0)

active_vms = []  # Track active VMs including original ones

for i, (vm, cloudlet) in enumerate(vm_cl_pairs):
    vm.assign_cloudlet(cloudlet)
    success = scheduler.schedule_vm(vm)
    if not success:
        print(f"VM {vm.vm_id} could not be scheduled!")
    expiration_step = 288  # run full 24 hours
    active_vms.append((vm, cloudlet, expiration_step))

# -----------------------------
# Dynamic VM Arrival and Removal
# -----------------------------
protean = ProteanSampler()
arrival_rates = protean.VM_arrival_rates(scale = num_peak_arrive)  # Scale as needed
vm_counter = num_initial_vms

# -----------------------------
# Simulation Loop
# -----------------------------
time_step = 300.0
current_time = 0.0
total_energy_joules = 0.0
host_utilization_history = {host.host_id: [] for host in hosts}

print("Start 24-hour simulation with dynamic VM management...\n")

num_active_vm = []

for t in range(288):
    # Step 1: Remove expired VMs
    for vm, cl, exp in active_vms:
        if t >= exp:
            for host in hosts:
                if any(v.vm_id == vm.vm_id for v in host.vms):
                    host.deallocate_vm(vm.vm_id)
                    break
    active_vms = [(vm, cl, exp) for (vm, cl, exp) in active_vms if t < exp]
    num_active_vm.append(len(active_vms))
    for i, (vm, cl, exp) in enumerate(active_vms):
        if vm.vm_id < num_initial_vms:
            # original VMs use fixed trace
            cpu_ratio = trace_data[vm.vm_id][t]
            cl.set_cpu_demand_ratio(cpu_ratio, current_time)
        else:
            # dynamically added VMs use a sampled trace
            trace_index = vm.vm_id % len(trace_data)
            cpu_ratio = trace_data[trace_index][t]
            cl.set_cpu_demand_ratio(cpu_ratio, current_time)
        cl.update_execution(current_time, time_step)
    if t > 289:
        breakpoint()
    # Step 2: Add new VMs based on arrival rate
    new_vm_count = int(arrival_rates[t])
    if new_vm_count > 0:
        lifetimes = protean.VM_lifetime(new_vm_count)
        for i in range(new_vm_count):
            new_vm = create_vm_list(1, start_id=vm_counter)[0]
            new_cloudlet = Cloudlet(f"D{t}_{i}", length=1e10)
            trace = random.choice(list(trace_data.values()))
            cpu_ratio = trace[t]
            new_cloudlet.set_cpu_demand_ratio(cpu_ratio, current_time)
            new_vm.assign_cloudlet(new_cloudlet)

            expiration_step = t + int(np.ceil(lifetimes[i] / 5))
            active_vms.append((new_vm, new_cloudlet, expiration_step))
            scheduler.schedule_vm(new_vm)
            vm_counter += 1

    # Step 3: Update energy and utilization
    for host in hosts:
        power = host.power_consumption()
        energy = power * time_step
        total_energy_joules += energy
        host_utilization_history[host.host_id].append(host.base_cpu_utilization())
        print(f"[{host.host_id}] Step {t:03d} | CPU Util: {host.base_cpu_utilization():.2f} | Power: {power:.2f} W | Energy: {energy:.2f} J")

    # Step 4: Migration from underutilized hosts
    current_util_map = {host.host_id: host.base_cpu_utilization() for host in hosts}
    underutilized_hosts = sorted(
        [h for h in hosts if current_util_map[h.host_id] < 0.2 and h.active],
        key=lambda h: current_util_map[h.host_id]
    )
    non_underutilized_hosts = sorted(
        [h for h in hosts if current_util_map[h.host_id] >= 0.2 and h.active],
        key=lambda h: current_util_map[h.host_id]
    )
    projected_util_map = {host.host_id: host.base_cpu_utilization() for host in hosts}

    for src_host in underutilized_hosts:
        src_vms = src_host.vms[:]
        vm_to_target_map = {}
        for vm in src_vms:
            placed = False
            candidate_hosts = non_underutilized_hosts + [
                h for h in hosts if h.active and h != src_host and h not in non_underutilized_hosts
            ]
            for target_host in candidate_hosts:
                host_id = target_host.host_id
                proj_util = projected_util_map[host_id]
                if (proj_util + vm.cpu / target_host.base_core_capacity) <= 0.8:
                    vm_to_target_map[vm.vm_id] = target_host
                    projected_util_map[host_id] += vm.cpu / target_host.base_core_capacity
                    placed = True
                    break
            if not placed:
                vm_to_target_map = {}
                print(f"[Step {t:03d}] Host {src_host.host_id} cannot migrate all VMs — skipping.")
                break

        if vm_to_target_map:
            for vm in src_vms:
                target_host = vm_to_target_map[vm.vm_id]
                src_host.deallocate_vm(vm.vm_id)
                target_host.allocate_vm(vm)
                vm.current_host = target_host
            src_host.power_off()
            print(f"[Step {t:03d}] Host {src_host.host_id} underutilized. All VMs migrated. Host powered off.")

    current_time += time_step

# -----------------------------
# Final Report
# -----------------------------
print(f"\nTotal Energy Consumption Over 24 Hours: {total_energy_joules:.2f} J = {total_energy_joules / 3600000:.6f} kWh")

# -----------------------------
# Visualization
# -----------------------------
time_axis = [i * 5 for i in range(288)]

plt.figure(figsize=(14, 6))
for i in range(min(num_initial_vms, 20)):
    plt.plot(time_axis, trace_data[i], label=f"VM{i+1}", alpha=0.7)
plt.title("CPU Utilization of Initial VMs Over 24 Hours")
plt.xlabel("Time (minutes)")
plt.ylabel("CPU Utilization (0–1)")
plt.grid(True)
plt.tight_layout()
plt.legend(ncol=4, fontsize='small', loc='upper center', bbox_to_anchor=(0.5, -0.15))
plt.show()

plt.figure(figsize=(14, 6))
for host_id, util_trace in host_utilization_history.items():
    plt.plot(time_axis, util_trace, label=host_id, alpha=0.8)
plt.title("CPU Utilization of Hosts Over 24 Hours")
plt.xlabel("Time (minutes)")
plt.ylabel("CPU Utilization (0–1)")
plt.grid(True)
plt.tight_layout()
plt.legend(ncol=4, fontsize='small', loc='upper center', bbox_to_anchor=(0.5, -0.15))
plt.show()

print(num_active_vm)