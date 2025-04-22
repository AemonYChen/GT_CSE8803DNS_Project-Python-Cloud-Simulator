# Helper.py

from datacenter import Host, VM
import random

# ====================
# Host Configuration
# ====================
HOST_TYPES = 2
HOST_MIPS = [1860, 2660]
HOST_PES = [2, 2]
HOST_RAM = [4096, 4096]
HOST_BW = 1000000
HOST_STORAGE = 1000000
HOST_Power_Idle = [60, 60]
HOST_Power_Full = [120, 140]

def create_host_list(num_hosts):
    hosts = []
    for i in range(num_hosts):
        type_id = i % HOST_TYPES

        host = Host(
            host_id=i,
            num_cores=HOST_PES[type_id],
            core_capacity=HOST_MIPS[type_id],
            ram_capacity=HOST_RAM[type_id],
            storage_capacity=HOST_STORAGE,
            power_idle=HOST_Power_Idle[type_id],
            power_max=HOST_Power_Full[type_id]
        )
        hosts.append(host)
    return hosts


# ====================
# VM Configuration
# ====================
VM_TYPES = 4
# VM_MIPS = [2500, 2000, 1000, 500]
VM_MIPS = [x / 2 for x in [2500, 2000, 1000, 500]]
VM_PES  = [1,    1,    1,    1]
#VM_RAM  = [870,  1740, 1740, 613]
#VM_BW   = 100000  # 100 Mbit/s (not used here)
#VM_SIZE = 2500    # 2.5 GB
VM_RAM  = [5,  5, 5, 5]
VM_BW   = 5  # 100 Mbit/s (not used here)
VM_SIZE = 5    # 2.5 GB

def create_vm_list(num_vms, start_id = 0, online_service=False):
    vm_list = []
    for i in range(num_vms):
        vm_type = random.randint(0, VM_TYPES - 1)
        vm_id = start_id + i
        cpu = VM_MIPS[vm_type] * VM_PES[vm_type]
        ram = VM_RAM[vm_type]
        storage = VM_SIZE
        vm = VM(vm_id, cpu=cpu, ram=ram, storage=storage, is_online_service=online_service)
        vm_list.append(vm)
    return vm_list