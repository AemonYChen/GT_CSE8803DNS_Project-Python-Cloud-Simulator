# Create a VM with a workload trace and simulate it over 24 hours with 1-hour intervals.

from datacenter import Cloudlet
from Helper import create_host_list, create_vm_list

# Simulated CPU demand ratios for each hour (0.0 to 1.0)
hourly_cpu_ratios = [
    0.2, 0.1, 0.1, 0.1, 0.2, 0.4, 0.6, 0.8, 0.9, 1.0, 0.9, 0.8,
    0.7, 0.6, 0.5, 0.6, 0.8, 0.9, 1.0, 0.9, 0.7, 0.5, 0.3, 0.2
]

# -----------------------------------
# Create one host and one VM using Helper
# -----------------------------------
hosts = create_host_list(1)
vms = create_vm_list(1)

host = hosts[0]
vm = vms[0]
host.allocate_vm(vm)

# Create a cloudlet with a long workload 
cloudlet = Cloudlet("C1", length=1e10)
vm.assign_cloudlet(cloudlet)

# Simulation parameters
total_energy_joules = 0.0
time_step = 3600.0  # 1 hour in seconds
current_time = 0.0

# DVFS Setting
host.enable_dvfs(False)

print("Start 24-hour simulation...\n")

# Simulation loop
for hour, cpu_ratio in enumerate(hourly_cpu_ratios):
    cloudlet.set_cpu_demand_ratio(cpu_ratio, current_time)
    cloudlet.update_execution(current_time, time_step)
    
    power = host.power_consumption()  # in Watts
    energy = power * time_step        # in Joules
    total_energy_joules += energy

    print(f"Hour {hour:02d} | CPU Ratio: {host.cpu_utilization():.2f} | Power: {power:.2f} W | "
          f"Energy: {energy:.2f} J | Total: {total_energy_joules:.2f} J")

    current_time += time_step

# Final energy report
print(f"\nTotal Energy Consumption Over 24 Hours: {total_energy_joules:.2f} J = "
      f"{total_energy_joules / 3600000:.6f} kWh")