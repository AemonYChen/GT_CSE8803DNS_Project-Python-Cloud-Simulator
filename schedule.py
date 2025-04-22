# schedule.py
import random

class SchedulerVM:
    def __init__(self, hosts, policy="first_fit"):
        """
        Scheduler to assign VMs to Hosts based on a given policy.

        :param hosts: list of Host objects
        :param policy: scheduling strategy ("first_fit", "least_utilized", etc.)
        """
        self.hosts = hosts
        self.policy = policy
        self.boot_energy_total = 0.0  # Track total boot energy
        
    def schedule_vm(self, vm):
        """
        Assigns a VM to a suitable host based on selected policy.
        Returns True if scheduling succeeded, False otherwise.
        """
        candidate_host = self._select_host(vm)

        if candidate_host:
            if not candidate_host.active:
                candidate_host.power_on()
                self.boot_energy_total += candidate_host.boot_energy_joules

            candidate_host.allocate_vm(vm)
            print(f"Scheduler: VM {vm.vm_id} assigned to Host {candidate_host.host_id} using '{self.policy}'")
            return True
        else:
            print(f"Scheduler: No suitable host found for VM {vm.vm_id} with policy '{self.policy}'")
            return False

    def _select_host(self, vm):
        """
        Internal method to select host based on policy.
        """
        if self.policy == "first_fit":
            return self._first_fit(vm)
        elif self.policy == "random":
            return self._random(vm)
        elif self.policy == "least_utilized":
            return self._least_utilized(vm)        
        elif self.policy == "most_utilized":
            return self._most_utilized(vm)
        elif self.policy == "best_fit":
            return self._best_fit(vm)
        elif self.policy == "worst_fit":
            return self._worst_fit(vm)
        elif self.policy == "energy_aware":
            return self._energy_aware(vm)
        elif self.policy == "most_free_ram":
            return self._most_free_ram(vm)
        # Future: elif self.policy == "energy_aware":
        else:
            raise ValueError(f"Unknown scheduling policy: {self.policy}")

    def _first_fit(self, vm):
        for host in self.hosts:
            if host.can_host_vm(vm):
                return host
        return None

    def _random(self, vm):
        candidates = [h for h in self.hosts if h.can_host_vm(vm)]
        if not candidates:
            return None
        return random.choice(candidates)

    def _least_utilized(self, vm):
        candidates = [h for h in self.hosts if h.can_host_vm(vm)]
        if not candidates:
            return None
        return min(candidates, key=lambda h: h.cpu_utilization())
    
    def _most_utilized(self, vm):
        candidates = [h for h in self.hosts if h.can_host_vm(vm)]
        if not candidates:
            return None
        return max(candidates, key=lambda h: h.cpu_utilization())

    def _best_fit(self, vm):
        candidates = [h for h in self.hosts if h.can_host_vm(vm)]
        if not candidates:
            return None
        return min(candidates, key=lambda h: (h.remaining_cpu() - vm.cpu))

    def _worst_fit(self, vm):
        candidates = [h for h in self.hosts if h.can_host_vm(vm)]
        if not candidates:
            return None
        return max(candidates, key=lambda h: (h.remaining_cpu() - vm.cpu))
    
    def _most_free_ram(self, vm):
        candidates = [h for h in self.hosts if h.can_host_vm(vm)]
        if not candidates:
            return None
        return max(candidates, key=lambda h: h.ram_capacity - sum(v.ram for v in h.vms))
    
    def _energy_aware(self, vm):
        candidates = [h for h in self.hosts if h.can_host_vm(vm)]
        if not candidates:
            return None

        vm_cpu_u_store = vm.cloudlet.cpu_demand_ratio
        vm.cloudlet.cpu_demand_ratio = vm.cloudlet.trace_mean

        def energy_increase_if_placed(host):
            original_energy = host.power_consumption()
            # Temporarily add the VM
            host.vms.append(vm)
            # Recalculate DVFS if enabled
            if host.dvfs_enabled:
                host.update_dvfs()
            new_energy = host.power_consumption()
            # Remove the VM after simulation
            host.vms.remove(vm)
            # Restore DVFS to reflect previous state
            if host.dvfs_enabled:
                host.update_dvfs()
            return new_energy - original_energy
        
        best_host = min(candidates, key=energy_increase_if_placed)

        # Restore the original demand ratio
        vm.cloudlet.cpu_demand_ratio = vm_cpu_u_store

        return best_host

    def set_policy(self, policy):
        self.policy = policy

    def get_total_boot_energy(self):
        return self.boot_energy_total