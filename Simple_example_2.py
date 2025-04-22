# A simple test includes two servers, four VMs, and four tasks.

from datacenter import Host, VM, Cloudlet

# ----- SETUP HOSTS -----
hosts = [
    Host("H1", num_cores=4, core_capacity=2500, ram_capacity=16000, storage_capacity=1000,
         cpu_oversub=1.0, power_idle=80, power_max=200),
    Host("H2", num_cores=8, core_capacity=2200, ram_capacity=32000, storage_capacity=2000,
         cpu_oversub=1.2, power_idle=100, power_max=250),
]

# ----- SETUP VMs -----
vms = [
    VM("VM1", cpu=2000, ram=4096, storage=100),
    VM("VM2", cpu=3000, ram=8192, storage=200),
    VM("VM3", cpu=2500, ram=6144, storage=150),
    VM("VM4", cpu=1500, ram=2048, storage=80),
]

# Allocate VMs to Hosts
hosts[0].allocate_vm(vms[0])  # VM1 to H1
hosts[0].allocate_vm(vms[1])  # VM2 to H1
hosts[1].allocate_vm(vms[2])  # VM3 to H2
hosts[1].allocate_vm(vms[3])  # VM4 to H2

# ----- SETUP CLOUDLETS -----
cloudlets = [
    Cloudlet("C1", length=10000, cpu_demand_ratio=0.5),
    Cloudlet("C2", length=15000, cpu_demand_ratio=0.7),
    Cloudlet("C3", length=8000, cpu_demand_ratio=0.6),
    Cloudlet("C4", length=12000, cpu_demand_ratio=0.4),
]

# Assign cloudlets to VMs
vms[0].assign_cloudlet(cloudlets[0])
vms[1].assign_cloudlet(cloudlets[1])
vms[2].assign_cloudlet(cloudlets[2])
vms[3].assign_cloudlet(cloudlets[3])

# ----- SIMULATION LOOP -----
print("\nStart Simulation")
current_time = 0.0
time_step = 1.0  # seconds
total_energy_joules = 0.0

# Run while any cloudlet is not finished
while any(not cl.finished for cl in cloudlets):
    for vm in vms:
        vm.update_cloudlets(current_time, time_step)

    for host in hosts:
        # Check if host has any running cloudlets
        active_cloudlets = any(
            not cl.finished
            for vm in host.vms
            for cl in vm.cloudlets
        )

        # Power and energy tracking only when host is active
        power = host.power_consumption()
        energy = power * time_step
        total_energy_joules += energy

        print(f"[{host.host_id}] Time {current_time:.1f}s | Active: {host.active} | "
            f"CPU Util: {host.base_cpu_utilization():.2%} | Power: {power:.2f} W | "
            f"Energy: {energy:.2f} J")
        
        # Power off if no active VMs/cloudlets
        if not active_cloudlets and host.active:
            host.power_off()

    current_time += time_step

# ----- FINAL STATS -----
print("\nSimulation Complete!")
print(f"Total Energy Consumed: {total_energy_joules:.2f} J = {total_energy_joules / 3600000:.6f} kWh")
for cl in cloudlets:
    print(f"Cloudlet {cl.cloudlet_id} finished at time {cl.end_time:.1f}s")