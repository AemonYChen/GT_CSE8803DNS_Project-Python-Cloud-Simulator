# Create mutiple VMs with random workload traces and simulate them over 24 hours with 1-hour intervals.
# Investigate how DVFS combined with VM allocation policies affects power consumption.

from datacenter import Cloudlet
from Helper import create_host_list, create_vm_list
from schedule import SchedulerVM
import numpy as np
import random

# -----------------------------
# Simulation Setup
# -----------------------------

random.seed(42)
np.random.seed(42)

# Step 1: Create 8 hosts
hosts = create_host_list(8)

# Step 2: Create 20 VMs
vms = create_vm_list(20)

# Step 3: Create 20 Cloudlets and bind each to a VM
cloudlets = [Cloudlet(f"C{i+1}", length=1e10) for i in range(20)]

# Step 4: Schedule the VMs using SchedulerVM
scheduler = SchedulerVM(hosts)

# -----------------------------
# VM Placement Policy and Host Configuration
# -----------------------------
# Set VM placement strategy
# scheduler.set_policy("least_utilized")

# Enable/Disable DVFS on all hosts
for host in hosts:
    host.enable_dvfs(False)
    if not host.vms and host.active:
        host.power_off()

for vm, cloudlet in zip(vms, cloudlets):
    success = scheduler.schedule_vm(vm)
    if success:
        vm.assign_cloudlet(cloudlet)
    else:
        print(f"VM {vm.vm_id} could not be scheduled!")
        breakpoint()

# -----------------------------
# Simulation Parameters
# -----------------------------

time_step = 3600.0  # 1 hour in seconds
current_time = 0.0
total_energy_joules = 0.0

# -----------------------------
# Simulation Loop
# -----------------------------
print("Start 24-hour simulation...\n")

for hour in range(24):
    for cloudlet in cloudlets:
        # Randomly generate CPU utilization using a Beta distribution (peak ≈ 0.3)

        cpu_ratio = np.random.beta(2.6, 4.73)
        cloudlet.set_cpu_demand_ratio(cpu_ratio, current_time)

    # Calculate power consumption
    for host in hosts:
        power = host.power_consumption()
        energy = power * time_step
        total_energy_joules += energy

        print(f"[{host.host_id}] Hour {hour:02d} | CPU Util: {host.cpu_utilization():.2f} | "
              f"Power: {power:.2f} W | Energy: {energy:.2f} J")

    current_time += time_step

# -----------------------------
# Final Report
# -----------------------------
print(f"\nTotal Energy Consumption Over 24 Hours: {total_energy_joules:.2f} J = "
      f"{total_energy_joules / 3600000:.6f} kWh")