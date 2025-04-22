# A simple test includes one server, one VM, and one task.

from datacenter import Host, VM, Cloudlet

host = Host("H1", num_cores=2, core_capacity=2500, ram_capacity=16000, storage_capacity=1000,
            cpu_oversub=1.0, power_idle=80, power_max=200)

# Create a VM with 2000 MIPS
vm = VM("VM1", cpu=2000, ram=4096, storage=100)
host.allocate_vm(vm)

# Create and assign a Cloudlet requiring 3000 MI
cloudlet = Cloudlet("C1", length=3000, cpu_demand_ratio=0.5)
vm.assign_cloudlet(cloudlet)

# Simulate execution
print(f"Start Simulation")
current_time = 0.0
time_step = 1.0  # seconds
total_energy_joules = 0.0  # initialize energy tracker

while not cloudlet.finished:
    cloudlet.update_execution(current_time, time_step)

    # Get power draw from host and compute energy
    power = host.power_consumption()  # in Watts
    energy = power * time_step        # in Joules
    total_energy_joules += energy

    print(f"Time {current_time:.1f}s - {cloudlet} | Power: {power:.2f} W | "
          f"Total Energy: {total_energy_joules:.2f} J")

    current_time += time_step

# Print final summary in kWh
print(f"\nCloudlet {cloudlet.cloudlet_id} completed in {current_time:.1f}s")
print(f"Total Energy Consumption: {total_energy_joules:.2f} J = "
      f"{total_energy_joules / 3600000:.6f} kWh")

