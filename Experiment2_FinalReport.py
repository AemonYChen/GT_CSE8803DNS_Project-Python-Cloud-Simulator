import matplotlib.pyplot as plt
import numpy as np

from datacenter import Host, VM, Cloudlet
from schedule import SchedulerVM

def set_dvfs_levels(host_instance, level, scaling, power_idle, power_max):
    host_instance.dvfs_levels[level]['scaling'] = scaling
    host_instance.dvfs_levels[level]['power_idle'] = power_idle
    host_instance.dvfs_levels[level]['power_max'] = power_max

def configure_case(case_id, scheduler, hosts):

    # Configure according to case_id:
    if case_id in [1, 2]:
        scheduler.set_policy("first_fit")
        if case_id == 2:
            for h in hosts:
                h.power_off()
    else:
        # For cases 3 to 8: enable DVFS and configure host parameters
        for h in hosts:
            scheduler.set_policy("least_utilized")
            if case_id == 4:
                h.apply_dvfs_level(2)
            elif case_id == 5:
                set_dvfs_levels(h, level=2, scaling=0.6,
                                power_idle=h.power_idle,
                                power_max=h.power_idle + (h.power_max - h.power_idle) * 0.216)
                h.apply_dvfs_level(2)
            elif case_id == 6:
                set_dvfs_levels(h, level=2, scaling=0.6,
                                power_idle=h.power_idle * 0.6,
                                power_max=h.power_max * 0.6)
                h.apply_dvfs_level(2)
            elif case_id == 7:
                set_dvfs_levels(h, level=2, scaling=0.6,
                                power_idle=h.power_idle * 0.75,
                                power_max=h.power_max * 0.65)
                h.apply_dvfs_level(2)
            elif case_id == 8:
                set_dvfs_levels(h, level=2, scaling=0.6,
                                power_idle=h.power_idle * 0.94,
                                power_max=h.power_max * 0.78)
                h.apply_dvfs_level(2)

def get_dynamic_arrivals(scenario_id):
    # Return workload list based on scenario load:
    if scenario_id == 1:
        # Scenario 1: 0.6 Load (15 VM-Cloudlet pairs)
        dynamic_arrivals = [
            (0.0, f"VM{i+1}", Cloudlet(f"C{i+1}", length=100, cpu_demand_ratio=1.0), 2000)
            for i in range(15)
        ]
    elif scenario_id == 2:
        # Scenario 2: 0.4 Load (10 VM-Cloudlet pairs)
        dynamic_arrivals = [
            (0.0, f"VM{i+1}", Cloudlet(f"C{i+1}", length=100, cpu_demand_ratio=1.0), 2000)
            for i in range(10)
        ]
    elif scenario_id == 3:
        # Scenario 3: 0.2 Load (5 VM-Cloudlet pairs)
        dynamic_arrivals = [
            (0.0, f"VM{i+1}", Cloudlet(f"C{i+1}", length=100, cpu_demand_ratio=1.0), 2000)
            for i in range(5)
        ]
    return dynamic_arrivals

def run_simulation(scenario_id, case_id):
    # Initialize hosts
    hosts = [
        Host(f"H{i+1}", num_cores=2, core_capacity=5000, ram_capacity=16000,
             storage_capacity=1000, power_idle=80, power_max=200)
        for i in range(5)
    ]
    
    # Create scheduler
    scheduler = SchedulerVM(hosts)
    # Configure hosts based on the case_id
    configure_case(case_id, scheduler, hosts)
    
    # Get dynamic arrivals based on load scenario
    dynamic_arrivals = get_dynamic_arrivals(scenario_id)
    
    active_vms = []
    cloudlets = []
    
    print(f"\n=== Starting Simulation: Scenario {scenario_id} | Case {case_id} ===")
    current_time = 0.0
    time_step = 1.0
    total_energy_joules = 0.0
    
    # Simulation loop
    while True:
        still_running = any(not cl.finished for cl in cloudlets)
        still_waiting = bool(dynamic_arrivals)
        if not still_running and not still_waiting:
            break

        # Inject new VM+Cloudlet arrivals
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
                    
        # Update hosts energy consumption and power management
        for host in hosts:  
            power = host.power_consumption()
            energy = power * time_step
            total_energy_joules += energy
            print(f"[{host.host_id}] Time {current_time:.1f}s | Active: {host.active} | CPU Util: {host.cpu_utilization():.2%} | Power: {power:.2f} W | Energy: {energy:.2f} J")
        
        # Update active VMs and cloudlets
        for vm in active_vms[:]:
            vm.update_cloudlets(current_time, time_step)
            if all(cl.finished for cl in vm.cloudlets):
                for host in hosts:
                    if vm in host.vms:
                        host.vms.remove(vm)
                        print(f"[Time {current_time:.1f}s] VM {vm.vm_id} deallocated from Host {host.host_id}")
                        break
                active_vms.remove(vm)
        
        current_time += time_step

    # Final simulation outputs
    print("\nSimulation Complete!")
    print(f"Scenario {scenario_id}, Case {case_id}: Total Energy Consumed: {total_energy_joules:.2f} J = {total_energy_joules / 3600000:.6f} kWh")
    for cl in cloudlets:
        print(f"Cloudlet {cl.cloudlet_id} finished at time {cl.end_time:.1f}s")
    
    return total_energy_joules  # Optionally return this value for further aggregation

if __name__ == '__main__':
    # Loop through all scenarios (1 to 3) and all cases (1 to 8)
    results = {}  # To store energy consumption results
    for scenario in range(1, 4):
        results[scenario] = {}
        for case in range(1, 9):
            energy = run_simulation(scenario, case)
            results[scenario][case] = energy
            print("-" * 60)
    
    # Print summary of results
    print("\n=== Summary of Total Energy Consumption (Joules) ===")
    for scenario in sorted(results.keys()):
        print(f"\nScenario {scenario}:")
        for case in sorted(results[scenario].keys()):
            print(f"  Case {case}: {results[scenario][case]:.2f} J")

    # Plotting
    scenario_ids = sorted(results.keys())
    case_ids = sorted(results[scenario_ids[0]].keys())
    num_scenarios = len(scenario_ids)
    num_cases = len(case_ids)

    # ---------- Bar Chart ----------
    bar_width = 0.1
    x = np.arange(num_scenarios)

    plt.figure(figsize=(12, 6))

    for i, case in enumerate(case_ids):
        y = [results[scenario][case] for scenario in scenario_ids]
        plt.bar(x + i * bar_width, y, width=bar_width, label=f"Case {case}")

    plt.xlabel("Scenario")
    plt.ylabel("Total Power (Watts)")
    plt.title("Energy Consumption by Scenario and Case")
    plt.xticks(x + bar_width * (num_cases - 1) / 2, [f"Scenario {sid}" for sid in scenario_ids])
    plt.legend(title="Case ID", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, axis='y')
    plt.tight_layout()
    plt.show()

    # ---------- Heatmap ----------
    heatmap_data = np.array([[results[sc][cs] for cs in case_ids] for sc in scenario_ids])

    plt.figure(figsize=(10, 5))
    plt.imshow(heatmap_data, cmap='plasma', aspect='auto')  # bright, vivid color scheme
    plt.colorbar(label="Power (Watts)")
    plt.title("Energy Consumption Heatmap")
    plt.xlabel("Case ID")
    plt.ylabel("Scenario ID")
    plt.xticks(np.arange(num_cases), [f"Case {i+1}" for i in range(num_cases)])
    plt.yticks(np.arange(num_scenarios), [f"Scenario {i+1}" for i in range(num_scenarios)])
    plt.tight_layout()
    plt.show()
