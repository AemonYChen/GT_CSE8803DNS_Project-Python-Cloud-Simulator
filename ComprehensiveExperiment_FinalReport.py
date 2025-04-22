import random
import numpy as np
import pandas as pd
from schedule import SchedulerVM
from Helper import create_host_list
from Runner import run_simulation
from vm_profile_generator import (
    generate_initial_vm_profiles,
    generate_dynamic_vm_profiles
)

import sys
import os

def block_print():
    sys.stdout = open(os.devnull, 'w')

def enable_print():
    sys.stdout = sys.__stdout__

# Global configs
trace_dir = "planetlab/20110303"
num_hosts = 200
num_initial_vms = 400
num_peak_arrive = 150
time_steps = 288
step_duration_sec = 300  # 5 minutes

placement_policies = [
    "random", "first_fit", "least_utilized",
    "most_utilized", "best_fit", "worst_fit", "energy_aware"
]

dvfs_options = [False, True]
migration_options = ["disable", "default"] 

results = []

random.seed(42)
np.random.seed(42)

case_id = 1
for policy in placement_policies:
    for dvfs_flag in dvfs_options:
        for migrate_set in migration_options:

            print(f"\n=== Running Case {case_id} ===")
            print(f"Policy: {policy}, DVFS: {dvfs_flag}, Migration: {migrate_set}")
            block_print()
            if migrate_set == "default":
                migrate_set_map = None
            else:
                migrate_set_map = migrate_set
        
            # Re-create hosts for each run
            hosts = create_host_list(num_hosts)
            scheduler = SchedulerVM(hosts)
            scheduler.set_policy(policy)

            for host in hosts:
                host.enable_dvfs(dvfs_flag)

            # Generate VMs
            initial_profiles = generate_initial_vm_profiles(
                num_vms=num_initial_vms,
                trace_dir=trace_dir,
                long_lived_ratio=0.6
            )

            dynamic_profiles = generate_dynamic_vm_profiles(
                trace_dir=trace_dir,
                num_hosts=num_hosts,
                num_peak_arrive=num_peak_arrive,
                initial_vm_id=len(initial_profiles)
            )

            all_profiles = initial_profiles + dynamic_profiles
            all_profiles.sort(key=lambda p: p["arrival_time"])

            # Run simulation
            total_energy_joules, host_utilization_history, num_active_vm = run_simulation(
                all_profiles=all_profiles,
                hosts=hosts,
                scheduler=scheduler,
                step_duration_sec=step_duration_sec,
                time_steps=time_steps,
                migrate_fn=migrate_set_map
            )
            enable_print()

            # Save results
            energy_kwh = total_energy_joules / 3_600_000
            results.append({
                "case": case_id,
                "policy": policy,
                "dvfs": dvfs_flag,
                "migration": migrate_set,
                "energy_kwh": energy_kwh
            })

            print(f"Total Energy: {energy_kwh:.6f} kWh")
            case_id += 1
            #breakpoint()

# Print summary
print("\n--- Summary of All Cases ---")
for r in results:
    print(f"Case {r['case']}: {r['policy']}, DVFS={r['dvfs']}, Mig={r['migration']} => {r['energy_kwh']:.6f} kWh")

# Save the results
df = pd.DataFrame(results)
df.to_csv("results.csv", index=False)

print("\nResults saved to results.csv")