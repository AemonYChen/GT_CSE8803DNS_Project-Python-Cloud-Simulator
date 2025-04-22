# datacenter.py

class Host:
    def __init__(self, host_id, num_cores, core_capacity, ram_capacity, storage_capacity,
                 cpu_oversub=1.0, ram_oversub=1.0, storage_oversub=1.0,
                 power_idle=100.0, power_max=250.0, boot_energy_joules=500.0, power_function=None):
        self.host_id = host_id
        self.num_cores = num_cores
        self.base_core_capacity = core_capacity  # Store original core capacity
        self.base_cpu_capacity = num_cores * core_capacity  # Store original core capacity
        self.core_capacity = core_capacity       # Will be modified by DVFS
        self.ram_capacity = ram_capacity
        self.storage_capacity = storage_capacity
        self.cpu_oversub = cpu_oversub
        self.ram_oversub = ram_oversub
        self.storage_oversub = storage_oversub
        self.power_function = power_function
        self.boot_energy_joules = boot_energy_joules
        self.vms = []
        self.active = True
        self.dvfs_enabled = False  # DVFS is disenabled by default

        # Power model (can be updated via DVFS)
        self.power_idle = power_idle
        self.power_max = power_max

        # DVFS settings
        self.dvfs_levels = [
            {"level": 0, "scaling": 1.0, "power_idle": power_idle, "power_max": power_max},
            {"level": 1, "scaling": 0.8, "power_idle": power_idle * 0.87, "power_max": power_max * 0.83},
            {"level": 2, "scaling": 0.6, "power_idle": power_idle * 0.75, "power_max": power_max * 0.65},
        ]
        self.dvfs_rule_function = None  # By default, no external rule
        self.current_dvfs_level = 0
        self.apply_dvfs_level(0)

    @property
    def cpu_capacity(self):
        return self.num_cores * self.core_capacity

    def cpu_utilization(self):
        total_demand = 0.0
        for vm in self.vms:
            for cl in vm.cloudlets:
                if not cl.finished:
                    total_demand += vm.cpu * cl.cpu_demand_ratio
        return min(total_demand / self.cpu_capacity, 1.0)
    
    def base_cpu_utilization(self):
        total_demand = 0.0
        for vm in self.vms:
            for cl in vm.cloudlets:
                if not cl.finished:
                    total_demand += vm.cpu * cl.cpu_demand_ratio
        return min(total_demand / self.base_cpu_capacity, 1.0)

    def power_consumption(self):
        if self.dvfs_enabled:
            self.update_dvfs()
        u = self.cpu_utilization()
        if not self.active and u == 0:
            return 0.0
        if self.power_function:
            return self.power_function(u)
        return self.power_idle + (self.power_max - self.power_idle) * u

    def apply_dvfs_level(self, level):
        """
        Manually set DVFS level.
        """
        level_config = next((d for d in self.dvfs_levels if d["level"] == level), None)
        if level_config:
            self.current_dvfs_level = level
            self.core_capacity = int(self.base_core_capacity * level_config["scaling"])
            self.power_idle = level_config["power_idle"]
            self.power_max = level_config["power_max"]
            # print(f"[DVFS] Host {self.host_id} set to level {level} (scaling {level_config['scaling']})")
        else:
            print(f"[DVFS] Invalid level {level} for Host {self.host_id}")

    def update_dvfs(self):
        """
        Auto-adjust DVFS level based on CPU utilization.
        """
        util = self.base_cpu_utilization()
        # If an external DVFS update rule is provided, use it.
        if self.dvfs_rule_function:
            new_level = self.dvfs_rule_function(util)
            self.apply_dvfs_level(new_level)
        else:
            # Default DVFS rule
            if util < 0.6:
                self.apply_dvfs_level(2)
            elif util < 0.8:
                self.apply_dvfs_level(1)
            else:
                self.apply_dvfs_level(0)
    
    def set_dvfs_rule(self, rule_function):
        """
        Set an external rule to auto-adjust DVFS level based on utilization.
        The rule_function must accept utilization as input and return a level.
        """
        self.dvfs_rule_function = rule_function
        print(f"[DVFS] Host {self.host_id} DVFS rule function set.")

    def enable_dvfs(self, flag: bool):
        self.dvfs_enabled = flag
        print(f"[DVFS] Host {self.host_id} DVFS {'enabled' if flag else 'disabled'}")

    def set_dvfs_levels(self, levels):
        self.dvfs_levels = levels
        self.apply_dvfs_level(0)  # Reset to level 0 when new levels are set

    def set_power_function(self, func):
        self.power_function = func

    def power_on(self):
        self.active = True
        print(f"Host {self.host_id} is now ON.")

    def power_off(self):
        self.active = False
        print(f"Host {self.host_id} is now OFF.")

    def allocate_vm(self, vm):
        # if self.active and self.can_host_vm(vm):
        if self.active:
            self.vms.append(vm)
            print(f"VM {vm.vm_id} allocated to Host {self.host_id}.")
        else:
            print(f"Host {self.host_id} cannot allocate VM {vm.vm_id}.")

    def deallocate_vm(self, vm_id):
        for vm in self.vms:
            if vm.vm_id == vm_id:
                self.vms.remove(vm)
                print(f"VM {vm_id} deallocated from Host {self.host_id}.")
                return
        print(f"VM {vm_id} not found on Host {self.host_id}.")

    def can_host_vm(self, vm):
        total_cpu = sum(v.cpu for v in self.vms)
        total_ram = sum(v.ram for v in self.vms)
        total_storage = sum(v.storage for v in self.vms)
        return (total_cpu + vm.cpu <= self.base_cpu_capacity * self.cpu_oversub and
                total_ram + vm.ram <= self.ram_capacity * self.ram_oversub and
                total_storage + vm.storage <= self.storage_capacity * self.storage_oversub)

    def remaining_cpu(self):
        used_cpu = sum(v.cpu for v in self.vms)
        return self.base_cpu_capacity - used_cpu

    def __str__(self):
        return (f"Host {self.host_id} | Cores: {self.num_cores} x {self.core_capacity} MIPS "
                f"= {self.cpu_capacity} MIPS, RAM: {self.ram_capacity} MB, "
                f"Storage: {self.storage_capacity} GB")


class VM:
    def __init__(self, vm_id, cpu, ram, storage, is_online_service=False):
        """
        VM represents a virtual machine or container instance.

        :param vm_id: Unique identifier
        :param cpu: MIPS (Million Instructions Per Second)
        :param ram: RAM in MB
        :param storage: Storage in GB
        :param is_online_service: Flag indicating whether the VM is for online service
        """
        self.vm_id = vm_id
        self.cpu = cpu
        self.ram = ram
        self.storage = storage
        self.is_online_service = is_online_service  # Flag to indicate online service
        self.cloudlet = None  # A single cloudlet for online services
        self.cloudlets = []   # Multiple cloudlets for batch workloads

        if is_online_service:
            # Create a Cloudlet inside the VM if it's for online service
            self.cloudlet = Cloudlet(f"Cloudlet_{vm_id}", length=1e10)  # Can use a large length or define as needed
            self.assign_cloudlet(self.cloudlet)  # Automatically bind the cloudlet

    def assign_cloudlet(self, cloudlet):
        """
        Assign a Cloudlet to this VM.
        """
        self.cloudlets.append(cloudlet)
        cloudlet.assign_to_vm(self)

    def update_cloudlets(self, current_time, time_step=1.0, cpu_ratio=None):
        """
        Update execution for the assigned cloudlet (or cloudlets) and remove finished ones.
        For online service VMs, directly update the CPU demand ratio if cpu_ratio is provided.
        """
        if self.is_online_service and self.cloudlet:
            # For online services, directly set the CPU demand ratio based on the provided cpu_ratio
            if cpu_ratio is not None:
                self.set_cpu_demand_ratio(cpu_ratio, current_time)
            if self.cloudlet.finished:
                self.cloudlet = None  # Clear the cloudlet if finished
                print(f"Cloudlet {self.cloudlet.cloudlet_id} has finished and is removed from VM {self.vm_id}")
        else:
            # For batch workloads, process all assigned cloudlets
            for cloudlet in self.cloudlets[:]:  # Copy to safely remove while iterating
                cloudlet.update_execution(current_time, time_step)
                if cloudlet.finished:
                    self.cloudlets.remove(cloudlet)
                    print(f"Cloudlet {cloudlet.cloudlet_id} has finished and is removed from VM {self.vm_id}")

    def __str__(self):
        if self.is_online_service:
            return (f"VM {self.vm_id} | Online Service | CPU: {self.cpu} MIPS, RAM: {self.ram} MB, "
                    f"Storage: {self.storage} GB, Cloudlet: {self.cloudlet.cloudlet_id if self.cloudlet else 'None'}")
        else:
            return (f"VM {self.vm_id} | Batch Workload | CPU: {self.cpu} MIPS, RAM: {self.ram} MB, "
                    f"Storage: {self.storage} GB, Active Cloudlets: {len(self.cloudlets)}")
    
class Cloudlet:
    def __init__(self, cloudlet_id, length, cpu_demand_ratio=1.0):
        """
        :param cloudlet_id: Unique identifier
        :param length: Total workload in MI (Million Instructions)
        :param cpu_demand_ratio: Initial fraction of VM CPU requested (0 to 1)
        """
        self.cloudlet_id = cloudlet_id
        self.length = length
        self.cpu_demand_ratio = cpu_demand_ratio
        self.remaining = length
        self.assigned_vm = None
        self.start_time = None
        self.end_time = None
        self.finished = False

        # Store changing CPU demand over time
        self.cpu_demand_timeline = {}  # {time: cpu_demand_ratio}

        # Statistical features of the workload trace (e.g., mean, std, max, min)
        self.trace_mean = None

    def assign_to_vm(self, vm, current_time=-1.0):
        self.assigned_vm = vm
        self.start_time = current_time
        self.cpu_demand_timeline[current_time] = self.cpu_demand_ratio

    def update_execution(self, current_time, time_step=1.0):
        if self.finished or not self.assigned_vm:
            return

        # Log the current cpu_demand_ratio
        self.cpu_demand_timeline[current_time] = self.cpu_demand_ratio

        effective_mips = self.assigned_vm.cpu * self.cpu_demand_ratio
        executed = effective_mips * time_step
        self.remaining -= executed

        if self.remaining <= 0:
            self.remaining = 0
            self.finished = True
            self.end_time = current_time + time_step

    def set_cpu_demand_ratio(self, new_ratio, current_time):
        """
        Directly update cpu_demand_ratio and log it.
        """
        self.cpu_demand_ratio = new_ratio
        self.cpu_demand_timeline[current_time] = new_ratio
        # print(f"[Cloudlet {self.cloudlet_id}] CPU demand ratio updated to {new_ratio} at time {current_time}")

    def estimated_runtime(self):
        if not self.assigned_vm:
            return None
        return self.remaining / (self.assigned_vm.cpu * self.cpu_demand_ratio)

    def __str__(self):
        status = "Finished" if self.finished else f"{self.remaining:.2f} MI remaining"
        return f"Cloudlet {self.cloudlet_id} | {status}"