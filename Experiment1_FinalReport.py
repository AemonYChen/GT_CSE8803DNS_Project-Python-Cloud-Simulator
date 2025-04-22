from datacenter import Host, VM, Cloudlet
import matplotlib.pyplot as plt

# Storage for visualization
all_power_traces = []
all_energy_totals = []

def set_dvfs_levels(host_instance, level, scaling, power_idle, power_max):
    host_instance.dvfs_levels[level]['scaling'] = scaling
    host_instance.dvfs_levels[level]['power_idle'] = power_idle
    host_instance.dvfs_levels[level]['power_max'] = power_max

def run_case(case_id):
    print(f"\n--- Running Case {case_id} ---")
    # Initialize host and VM
    host = Host("H1", num_cores=2, core_capacity=5000, ram_capacity=16000, storage_capacity=1000,
                cpu_oversub=1.0, power_idle=80, power_max=200)
    vm = VM("VM1", cpu=10000, ram=4096, storage=100)
    host.allocate_vm(vm)

    if case_id == 1:
        cloudlet = Cloudlet("C1", length=30000, cpu_demand_ratio=1.0)

    elif case_id == 2:
        cloudlet = Cloudlet("C1", length=30000, cpu_demand_ratio=1.0)

    elif case_id == 3:
        host.apply_dvfs_level(2)
        cloudlet = Cloudlet("C1", length=30000, cpu_demand_ratio=0.6)

    elif case_id == 4:
        set_dvfs_levels(host, level=2, scaling=0.6,
                        power_idle=host.power_idle,
                        power_max=host.power_idle + (host.power_max - host.power_idle) * 0.216)
        host.apply_dvfs_level(2)
        cloudlet = Cloudlet("C1", length=30000, cpu_demand_ratio=0.6)

    elif case_id == 5:
        set_dvfs_levels(host, level=2, scaling=0.6,
                        power_idle=host.power_idle * 0.6,
                        power_max=host.power_max * 0.6)
        host.apply_dvfs_level(2)
        cloudlet = Cloudlet("C1", length=30000, cpu_demand_ratio=0.6)

    elif case_id == 6:
        set_dvfs_levels(host, level=2, scaling=0.6,
                        power_idle=host.power_idle * 0.75,
                        power_max=host.power_max * 0.65)
        host.apply_dvfs_level(2)
        cloudlet = Cloudlet("C1", length=30000, cpu_demand_ratio=0.6)

    elif case_id == 7:
        set_dvfs_levels(host, level=2, scaling=0.6,
                        power_idle=host.power_idle * 0.94,
                        power_max=host.power_max * 0.78)
        host.apply_dvfs_level(2)
        cloudlet = Cloudlet("C1", length=30000, cpu_demand_ratio=0.6)

    vm.assign_cloudlet(cloudlet)

    # Start simulation
    print(f"Start Simulation for Case {case_id}")
    current_time = 0.0
    time_step = 1.0
    total_energy_joules = 0.0
    power_trace = []

    while current_time < 5:
        power = host.power_consumption()
        energy = power * time_step
        total_energy_joules += energy
        power_trace.append(power)

        print(f"Time {current_time:.1f}s - {cloudlet} | Power: {power:.2f} W | Total Energy: {total_energy_joules:.2f} J")

        cloudlet.update_execution(current_time, time_step)

        if case_id == 2 and host.cpu_utilization() == 0:
            host.power_off()

        current_time += time_step

    print(f"Time {current_time:.1f}s - {cloudlet} | Total Energy: {total_energy_joules:.2f} J")
    print(f"Cloudlet {cloudlet.cloudlet_id} completed in {current_time:.1f}s")
    print(f"Total Energy Consumption: {total_energy_joules:.2f} J = {total_energy_joules / 3600000:.6f} kWh\n")

    return power_trace, total_energy_joules

def visualize_results():
    # --- Power per second plot ---
    plt.figure()
    for i, trace in enumerate(all_power_traces, 1):
        time = list(range(1, len(trace) + 1))
        if i == 1:
            stepped_time = time[:3] + [3, 4, 5]
            stepped_power = trace[:3] + [trace[3]] + trace[3:]
            plt.plot(stepped_time, stepped_power, label="Case 1", linestyle='-', marker='o')
        elif i == 2:
            offset_trace = [p + 0.5 for p in trace]
            stepped_time = time[:3] + [3, 4, 5]
            stepped_power = offset_trace[:3] + [offset_trace[3]] + offset_trace[3:]
            plt.plot(stepped_time, stepped_power, label="Case 2", linestyle='--', marker='s')
        else:
            plt.plot(time, trace, label=f"Case {i}")
    plt.xlabel("Time (s)")
    plt.ylabel("Power Consumption (W)")
    plt.title("Power Consumption Over Time")
    plt.legend()
    plt.grid(True)
    plt.show()

    # --- Total energy plot ---
    plt.figure()
    x_labels = [f"Case {i}" for i in range(1, 8)]

    # Case 1 split: first 3s = operating, last 2s = idle
    case1_operating = sum(all_power_traces[0][:3])
    case1_idle = sum(all_power_traces[0][3:])
    case2_operating = all_energy_totals[1]
    case12_operating  = [case1_operating, case2_operating]
    other_cases = all_energy_totals[2:]

    plt.bar(range(0,2), case12_operating, label="Case 1/2 - Operating")
    plt.bar(0, case1_idle, bottom=case1_operating, label="Case 1/2 - Idle")
    plt.bar(range(2, 7), other_cases, label="Case 3-7")

    plt.xticks(range(7), x_labels)
    plt.ylabel("Total Energy Consumption (Joules)")
    plt.title("Total Energy Consumption per Case")
    plt.legend()
    plt.grid(True)
    plt.show()

# Run all 7 cases and collect results
for case_id in range(1, 8):
    trace, total_energy = run_case(case_id)
    all_power_traces.append(trace)
    all_energy_totals.append(total_energy)

# Plot results
visualize_results()
