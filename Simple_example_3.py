# A test investigating how VM distribution (or different allocation policies) affects energy performance.
# Example 2 in the progress report.

from datacenter import Host, VM, Cloudlet
from schedule import SchedulerVM

# ----- SETUP HOSTS -----
hosts = [
    Host("H1", num_cores=4, core_capacity=2500, ram_capacity=16000, storage_capacity=1000,
         power_idle=80, power_max=200),
    Host("H2", num_cores=4, core_capacity=2500, ram_capacity=16000, storage_capacity=1000,
         power_idle=80, power_max=200),
    Host("H3", num_cores=4, core_capacity=2500, ram_capacity=16000, storage_capacity=1000,
         power_idle=80, power_max=200)
]

# ---- Make the Change Here ---- #
for h in hosts:
    h.power_off()
    h.enable_dvfs(False)
    h.apply_dvfs_level(2)


scheduler = SchedulerVM(hosts)
# ---- Make the Change Here ---- #
scheduler.set_policy("least_utilized")

# ----- Define dynamically arriving (VM + Cloudlet) tuples -----
dynamic_arrivals = [
    (0.0, "VM1", Cloudlet("C1", length=10000, cpu_demand_ratio=1.0), 1900),
    (0.0, "VM2", Cloudlet("C2", length=10000, cpu_demand_ratio=1.0), 1900),
    (0.0, "VM3", Cloudlet("C3", length=10000, cpu_demand_ratio=1.0), 1900),
    (0.0, "VM101", Cloudlet("C101", length=10000, cpu_demand_ratio=1.0), 1900),
    (0.0, "VM102", Cloudlet("C102", length=10000, cpu_demand_ratio=1.0), 1900),
    (0.0, "VM103", Cloudlet("C103", length=10000, cpu_demand_ratio=1.0), 1900),
    (0.0, "VM201", Cloudlet("C201", length=10000, cpu_demand_ratio=1.0), 1900),
    (0.0, "VM202", Cloudlet("C202", length=10000, cpu_demand_ratio=1.0), 1900),
    (0.0, "VM203", Cloudlet("C203", length=10000, cpu_demand_ratio=1.0), 1900),
]

# Track active VMs and cloudlets
active_vms = []
cloudlets = []

# ----- SIMULATION LOOP -----
print("\nStart Simulation")
current_time = 0.0
time_step = 1.0
total_energy_joules = 0.0

while True:
    # Exit when no more VMs/cloudlets and no arrivals left
    still_running = any(not cl.finished for cl in cloudlets)
    still_waiting = bool(dynamic_arrivals)
    if not still_running and not still_waiting:
        break

    # Inject VM+Cloudlet pairs based on arrival time
    for entry in dynamic_arrivals[:]:
        arrival_time, vm_id, cloudlet, cpu_capacity = entry
        if current_time >= arrival_time:
            vm = VM(vm_id, cpu=cpu_capacity, ram=0, storage=0)
            if scheduler.schedule_vm(vm):
                vm.assign_cloudlet(cloudlet)
                active_vms.append(vm)
                cloudlets.append(cloudlet)
                print(f"[Time {current_time:.1f}s] VM {vm.vm_id} with Cloudlet {cloudlet.cloudlet_id} started")
                dynamic_arrivals.remove(entry)

    # Update power and energy tracking for each host
    for host in hosts:
        # Power off if no VMs are left
        if not host.vms and host.active:
            host.power_off()

        power = host.power_consumption()
        energy = power * time_step
        total_energy_joules += energy

        print(f"[{host.host_id}] Time {current_time:.1f}s | Active: {host.active} | "
              f"CPU Util: {host.cpu_utilization():.2%} | Power: {power:.2f} W | "
              f"Energy: {energy:.2f} J")
        
    # Update all active VMs
    for vm in active_vms[:]:
        vm.update_cloudlets(current_time, time_step)
        # If cloudlet is finished, deallocate the VM from its host
        if all(cl.finished for cl in vm.cloudlets):
            for host in hosts:
                if vm in host.vms:
                    host.vms.remove(vm)
                    print(f"[Time {current_time:.1f}s] VM {vm.vm_id} deallocated from Host {host.host_id}")
                    break
            active_vms.remove(vm)

    current_time += time_step
    print(scheduler.get_total_boot_energy())

boot_energy = scheduler.get_total_boot_energy()
total_energy_joules += boot_energy

# ----- FINAL OUTPUT -----
print("\nSimulation Complete!")
print(f"Total Energy Consumed: {total_energy_joules:.2f} J = {total_energy_joules / 3600000:.6f} kWh")
for cl in cloudlets:
    print(f"Cloudlet {cl.cloudlet_id} finished at time {cl.end_time:.1f}s")