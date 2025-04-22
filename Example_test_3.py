# Create mutiple VMs with *PlanetLab* workload traces and simulate them over 24 hours with 5-min intervals.
# Investigate how DVFS combined with VM allocation policies affects power consumption.

import os
import random
import numpy as np
from datacenter import Cloudlet
from Helper import create_host_list, create_vm_list
from schedule import SchedulerVM
import matplotlib.pyplot as plt

# -----------------------------
# Simulation Setup
# -----------------------------
random.seed(42)
np.random.seed(42)

# Step 1: Create 12 hosts
hosts = create_host_list(20)

# Step 2: Create 20 VMs
num_vms = 40
vms = create_vm_list(num_vms)

# Step 3: Load num_vms unique PlanetLab traces
trace_dir = "planetlab/20110303"
trace_files = [f for f in os.listdir(trace_dir) if os.path.isfile(os.path.join(trace_dir, f))]

if len(trace_files) < num_vms:
    raise ValueError("Not enough trace files in the directory to assign unique traces to each cloudlet.")

selected_traces = random.sample(trace_files, num_vms)
trace_data = {}

for i, filename in enumerate(selected_traces):
    path = os.path.join(trace_dir, filename)
    with open(path, 'r') as f:
        values = [float(line.strip()) for line in f if line.strip().isdigit()]
    values = values[:288]  # 5-minute steps for 24 hours
    if len(values) < 288:
        raise ValueError(f"Trace file {filename} has fewer than 288 entries.")
    trace_data[i] = [min(max(v / 100.0, 0.0), 1.0) for v in values]

# Step 4: Create num_vms Cloudlets and bind each to a VM
cloudlets = [Cloudlet(f"C{i+1}", length=1e10) for i in range(num_vms)]

# Step 5: Schedule the VMs using SchedulerVM
scheduler = SchedulerVM(hosts)

# -----------------------------
# VM Placement Policy and Host Configuration
# -----------------------------
# Set VM placement strategy
scheduler.set_policy("best_fit")
    #first_fit
    #least_utilized
    #best_fit
    #worst_fit
    #energy_aware

# Enable/Disable DVFS on all hosts
for host in hosts:
    host.enable_dvfs(True)
    host.power_off()

# Sort VM–cloudlet pairs by VM.cpu (descending)
vm_cl_pairs = sorted(zip(vms, cloudlets), key=lambda pair: pair[0].cpu, reverse=True)

for i, cloudlet in enumerate(cloudlets):
    trace = trace_data[i]
    cpu_ratio = sum(trace) / len(trace) if trace else 0.0
    cloudlet.set_cpu_demand_ratio(cpu_ratio, 0)

for i, (vm, cloudlet) in enumerate(vm_cl_pairs):
    vm.assign_cloudlet(cloudlet)
    success = scheduler.schedule_vm(vm)
    if not success:
        print(f"VM {vm.vm_id} could not be scheduled!")

# -----------------------------
# Simulation Parameters
# -----------------------------
time_step = 300.0  # 5 minutes in seconds
current_time = 0.0
total_energy_joules = 0.0
host_utilization_history = {host.host_id: [] for host in hosts}

# -----------------------------
# Simulation Loop
# -----------------------------
print("Start 24-hour simulation using PlanetLab traces...\n")

for t in range(288):  # 288 steps = 24 hours at 5-min intervals
    for i, cloudlet in enumerate(cloudlets):
        cpu_ratio = trace_data[i][t]
        cloudlet.set_cpu_demand_ratio(cpu_ratio, current_time)
        cloudlet.update_execution(current_time, time_step)

    for host in hosts:
        power = host.power_consumption()
        energy = power * time_step
        total_energy_joules += energy

        # Record CPU utilization per host
        host_utilization_history[host.host_id].append(host.base_cpu_utilization())

        print(f"[{host.host_id}] Step {t:03d} | CPU Util: {host.base_cpu_utilization():.2f} | "
              f"Power: {power:.2f} W | Energy: {energy:.2f} J")
        

    # Dynamic VM migration every interval 
    current_util_map = {host.host_id: host.base_cpu_utilization() for host in hosts}
    underutilized_hosts = sorted(
        [host for host in hosts if current_util_map[host.host_id] < 0.2 and host.active],
        key=lambda h: current_util_map[h.host_id]
    )

    non_underutilized_hosts = sorted(
        [host for host in hosts if current_util_map[host.host_id] >= 0.2 and host.active],
        key=lambda h: current_util_map[h.host_id]
    )

    # Initialize projected utilizations with current values
    projected_util_map = {host.host_id: host.base_cpu_utilization() for host in hosts}

    for src_host in underutilized_hosts:
        src_vms = src_host.vms[:]
        vm_to_target_map = {}  # Temporarily store migration plan

        # Attempt to find placement for all VMs
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
                vm_to_target_map = {}  # Discard plan
                print(f"[Step {t:03d}] Host {src_host.host_id} cannot migrate all VMs — skipping.")
                break

        # Perform actual migration if all VMs were placed
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
print(f"\nTotal Energy Consumption Over 24 Hours: {total_energy_joules:.2f} J = "
      f"{total_energy_joules / 3600000:.6f} kWh")

# -----------------------------
# Visulization
# -----------------------------
time_axis = [i * 5 for i in range(288)]  # 5-min resolution

# ---------- VM Utilization Plot ----------
plt.figure(figsize=(14, 6))
for i in range(num_vms):
    plt.plot(time_axis, trace_data[i], label=f"VM{i+1}", alpha=0.7)
plt.title(f"CPU Utilization of {num_vms} VMs Over 24 Hours")
plt.xlabel("Time (minutes)")
plt.ylabel("CPU Utilization (0–1)")
plt.grid(True)
plt.tight_layout()
plt.legend(ncol=4, fontsize='small', loc='upper center', bbox_to_anchor=(0.5, -0.15))
plt.show()

# ---------- Host Utilization Plot ----------
plt.figure(figsize=(14, 6))
for host_id, util_trace in host_utilization_history.items():
    plt.plot(time_axis, util_trace, label=host_id, alpha=0.8)
plt.title("CPU Utilization of 12 Hosts Over 24 Hours")
plt.xlabel("Time (minutes)")
plt.ylabel("CPU Utilization (0–1)")
plt.grid(True)
plt.tight_layout()
plt.legend(ncol=4, fontsize='small', loc='upper center', bbox_to_anchor=(0.5, -0.15))
plt.show()