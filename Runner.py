import matplotlib.pyplot as plt
import numpy as np
from Helper import create_vm_list

def run_simulation(all_profiles, hosts, scheduler, step_duration_sec=300, time_steps=288, migrate_fn=None):
    current_time = 0.0
    total_energy_joules = 0.0
    active_vms = []
    host_utilization_history = {host.host_id: [] for host in hosts}
    num_active_vm = []

    # Create all VM objects before loop
    total_vm_count = len(all_profiles)
    vm_list = create_vm_list(total_vm_count,online_service=True)
    for vm, profile in zip(vm_list, all_profiles):
        vm.vm_id = profile["vm_id"]
    vm_objects = {vm.vm_id: vm for vm in vm_list}

    print("Start 24-hour simulation with dynamic VM management...\n")

    for t in range(time_steps):
        # Step 1: Add VMs arriving at this time
        for profile in [p for p in all_profiles if p["arrival_time"] == t]:
            vm = vm_objects[profile["vm_id"]]
            cpu_ratio = profile["cpu_utilization"][t]
            vm.cloudlet.set_cpu_demand_ratio(cpu_ratio, current_time)
            vm.cloudlet.trace_mean = np.mean(profile["cpu_utilization"])
            expiration_step = t + profile["lifetime"]
            success = scheduler.schedule_vm(vm)
            if success:
                active_vms.append((vm, expiration_step))
            else:
                print(f"[Step {t}] VM {vm.vm_id} could not be scheduled.")

        # Step 2: Update running VMs and remove expired
        remaining_vms = []
        for vm, exp in active_vms:
            if t >= exp:
                for host in hosts:
                    if vm in host.vms:
                        host.deallocate_vm(vm.vm_id)
                        break
            else:
                profile = next(p for p in all_profiles if p["vm_id"] == vm.vm_id)
                cpu_ratio = profile["cpu_utilization"][t]
                vm.cloudlet.set_cpu_demand_ratio(cpu_ratio, current_time)
                remaining_vms.append((vm, exp))
        active_vms = remaining_vms
        num_active_vm.append(len(active_vms))

        # Step 3: Power + utilization update
        for host in hosts:
            power = host.power_consumption()
            energy = power * step_duration_sec
            total_energy_joules += energy
            host_utilization_history[host.host_id].append(host.base_cpu_utilization())
            print(f"[{host.host_id}] Step {t:03d} | CPU Util: {host.base_cpu_utilization():.2f} | Power: {power:.2f} W | Energy: {energy:.2f} J")

        # Step 4: Migration or shutdown if idle
        if migrate_fn == "disable":
            for host in hosts:
                if host.active and len(host.vms) == 0:
                    host.power_off()
                    print(f"[Step {t:03d}] Host {host.host_id} is idle and powered off.")
        elif migrate_fn is not None:
            migrate_fn(hosts, current_time)
        else:
            migrate_vms(hosts, current_time)

        current_time += step_duration_sec

    return total_energy_joules, host_utilization_history, num_active_vm

def migrate_vms(hosts, current_time):
    current_util_map = {h.host_id: h.base_cpu_utilization() for h in hosts}
    underutilized_hosts = sorted(
        [h for h in hosts if current_util_map[h.host_id] < 0.2 and h.active],
        key=lambda h: current_util_map[h.host_id]
    )
    non_underutilized_hosts = sorted(
        [h for h in hosts if current_util_map[h.host_id] >= 0.2 and h.active],
        key=lambda h: current_util_map[h.host_id]
    )
    projected_util_map = current_util_map.copy()

    for src_host in underutilized_hosts:
        src_vms = src_host.vms[:]
        vm_to_target_map = {}
        for vm in src_vms:
            placed = False
            for target in non_underutilized_hosts + [h for h in hosts if h.active and h != src_host and h not in non_underutilized_hosts]:
                if projected_util_map[target.host_id] + vm.cpu / target.base_core_capacity <= 0.8:
                    vm_to_target_map[vm.vm_id] = target
                    projected_util_map[target.host_id] += vm.cpu / target.base_core_capacity
                    placed = True
                    break
            if not placed:
                vm_to_target_map = {}
                print(f"[Step {int(current_time/300):03d}] Host {src_host.host_id} cannot migrate all VMs — skipping.")
                break

        if vm_to_target_map:
            for vm in src_vms:
                src_host.deallocate_vm(vm.vm_id)
                target = vm_to_target_map[vm.vm_id]
                target.allocate_vm(vm)
            src_host.power_off()
            print(f"[Step {int(current_time/300):03d}] Host {src_host.host_id} underutilized. All VMs migrated. Host powered off.")

def plot_utilization(profiles, host_utilization_history, time_steps=288):
    time_axis = [i * 5 for i in range(time_steps)]

    plt.figure(figsize=(14, 6))

    for idx in np.random.choice(len(profiles), size=min(20, len(profiles)), replace=False):
        profile = profiles[idx]
        arrival_time = profile["arrival_time"]
        lifetime = profile["lifetime"]
        departure_time = arrival_time + lifetime
        utilization_trace = profile["cpu_utilization"]
        masked_util = [
            u if arrival_time <= t < departure_time else np.nan
            for t, u in enumerate(utilization_trace)
        ]

        valid_points = np.count_nonzero(~np.isnan(masked_util))
        if valid_points == 1:
            plt.plot(time_axis, masked_util, 'm+', label=f"VM {profile['vm_id']} (1 point)")
        else:
            plt.plot(time_axis, masked_util, label=f"VM {profile['vm_id']}", alpha=0.7)

    plt.title("CPU Utilization of Random 20 VMs Over 24 Hours")
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