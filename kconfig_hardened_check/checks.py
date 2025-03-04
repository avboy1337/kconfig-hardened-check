#!/usr/bin/python3

"""
This tool helps me to check Linux kernel options against
my security hardening preferences for X86_64, ARM64, X86_32, and ARM.
Let the computers do their job!

Author: Alexander Popov <alex.popov@linux.com>

This module contains knowledge for checks.
"""

# N.B. Hardening sysctls:
#    kernel.kptr_restrict=2 (or 1?)
#    kernel.dmesg_restrict=1 (also see the kconfig option)
#    kernel.perf_event_paranoid=2 (or 3 with a custom patch, see https://lwn.net/Articles/696216/)
#    kernel.kexec_load_disabled=1
#    kernel.yama.ptrace_scope=3
#    user.max_user_namespaces=0
#    what about bpf_jit_enable?
#    kernel.unprivileged_bpf_disabled=1
#    net.core.bpf_jit_harden=2
#    vm.unprivileged_userfaultfd=0
#        (at first, it disabled unprivileged userfaultfd,
#         and since v5.11 it enables unprivileged userfaultfd for user-mode only)
#    vm.mmap_min_addr has a good value
#    dev.tty.ldisc_autoload=0
#    fs.protected_symlinks=1
#    fs.protected_hardlinks=1
#    fs.protected_fifos=2
#    fs.protected_regular=2
#    fs.suid_dumpable=0
#    kernel.modules_disabled=1
#    kernel.randomize_va_space=2
#    nosmt sysfs control file
#    dev.tty.legacy_tiocsti=0
#
# Think of these boot params:
#    module.sig_enforce=1
#    lockdown=confidentiality
#    mce=0
#    nosmt=force
#    intel_iommu=on
#    amd_iommu=on
#    efi=disable_early_pci_dma

# pylint: disable=missing-function-docstring,line-too-long,invalid-name
# pylint: disable=too-many-branches,too-many-statements

from .engine import KconfigCheck, CmdlineCheck, VersionCheck, OR, AND


def add_kconfig_checks(l, arch):
    # Calling the KconfigCheck class constructor:
    #     KconfigCheck(reason, decision, name, expected)
    #
    # [!] Don't add CmdlineChecks in add_kconfig_checks() to avoid wrong results
    #     when the tool doesn't check the cmdline.

    efi_not_set = KconfigCheck('-', '-', 'EFI', 'is not set')
    cc_is_gcc = KconfigCheck('-', '-', 'CC_IS_GCC', 'y') # exists since v4.18
    cc_is_clang = KconfigCheck('-', '-', 'CC_IS_CLANG', 'y') # exists since v4.18

    modules_not_set = KconfigCheck('cut_attack_surface', 'kspp', 'MODULES', 'is not set')
    devmem_not_set = KconfigCheck('cut_attack_surface', 'kspp', 'DEVMEM', 'is not set') # refers to LOCKDOWN
    bpf_syscall_not_set = KconfigCheck('cut_attack_surface', 'lockdown', 'BPF_SYSCALL', 'is not set') # refers to LOCKDOWN

    # 'self_protection', 'defconfig'
    l += [KconfigCheck('self_protection', 'defconfig', 'BUG', 'y')]
    l += [KconfigCheck('self_protection', 'defconfig', 'SLUB_DEBUG', 'y')]
    l += [KconfigCheck('self_protection', 'defconfig', 'THREAD_INFO_IN_TASK', 'y')]
    gcc_plugins_support_is_set = KconfigCheck('self_protection', 'defconfig', 'GCC_PLUGINS', 'y')
    l += [gcc_plugins_support_is_set]
    iommu_support_is_set = KconfigCheck('self_protection', 'defconfig', 'IOMMU_SUPPORT', 'y')
    l += [iommu_support_is_set] # is needed for mitigating DMA attacks
    l += [OR(KconfigCheck('self_protection', 'defconfig', 'STACKPROTECTOR', 'y'),
             KconfigCheck('self_protection', 'defconfig', 'CC_STACKPROTECTOR', 'y'),
             KconfigCheck('self_protection', 'defconfig', 'CC_STACKPROTECTOR_REGULAR', 'y'),
             KconfigCheck('self_protection', 'defconfig', 'CC_STACKPROTECTOR_AUTO', 'y'),
             KconfigCheck('self_protection', 'defconfig', 'CC_STACKPROTECTOR_STRONG', 'y'))]
    l += [OR(KconfigCheck('self_protection', 'defconfig', 'STACKPROTECTOR_STRONG', 'y'),
             KconfigCheck('self_protection', 'defconfig', 'CC_STACKPROTECTOR_STRONG', 'y'))]
    l += [OR(KconfigCheck('self_protection', 'defconfig', 'STRICT_KERNEL_RWX', 'y'),
             KconfigCheck('self_protection', 'defconfig', 'DEBUG_RODATA', 'y'))] # before v4.11
    l += [OR(KconfigCheck('self_protection', 'defconfig', 'STRICT_MODULE_RWX', 'y'),
             KconfigCheck('self_protection', 'defconfig', 'DEBUG_SET_MODULE_RONX', 'y'),
             modules_not_set)] # DEBUG_SET_MODULE_RONX was before v4.11
    l += [OR(KconfigCheck('self_protection', 'defconfig', 'REFCOUNT_FULL', 'y'),
             VersionCheck((5, 5)))] # REFCOUNT_FULL is enabled by default since v5.5
    if arch in ('X86_64', 'ARM64', 'X86_32'):
        l += [KconfigCheck('self_protection', 'defconfig', 'RANDOMIZE_BASE', 'y')]
    if arch in ('X86_64', 'ARM64', 'ARM'):
        l += [KconfigCheck('self_protection', 'defconfig', 'VMAP_STACK', 'y')]
    if arch in ('X86_64', 'X86_32'):
        l += [KconfigCheck('self_protection', 'defconfig', 'DEBUG_WX', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'WERROR', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'X86_MCE', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'X86_MCE_INTEL', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'X86_MCE_AMD', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'MICROCODE', 'y')] # is needed for mitigating CPU bugs
        l += [KconfigCheck('self_protection', 'defconfig', 'RETPOLINE', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'SYN_COOKIES', 'y')] # another reason?
        l += [OR(KconfigCheck('self_protection', 'defconfig', 'X86_SMAP', 'y'),
                 VersionCheck((5, 19)))] # X86_SMAP is enabled by default since v5.19
        l += [OR(KconfigCheck('self_protection', 'defconfig', 'X86_UMIP', 'y'),
                 KconfigCheck('self_protection', 'defconfig', 'X86_INTEL_UMIP', 'y'))]
    if arch in ('ARM64', 'ARM'):
        l += [KconfigCheck('self_protection', 'defconfig', 'IOMMU_DEFAULT_DMA_STRICT', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'IOMMU_DEFAULT_PASSTHROUGH', 'is not set')] # true if IOMMU_DEFAULT_DMA_STRICT is set
        l += [KconfigCheck('self_protection', 'defconfig', 'STACKPROTECTOR_PER_TASK', 'y')]
    if arch == 'X86_64':
        l += [KconfigCheck('self_protection', 'defconfig', 'PAGE_TABLE_ISOLATION', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'RANDOMIZE_MEMORY', 'y')]
        l += [AND(KconfigCheck('self_protection', 'defconfig', 'INTEL_IOMMU', 'y'),
                  iommu_support_is_set)]
        l += [AND(KconfigCheck('self_protection', 'defconfig', 'AMD_IOMMU', 'y'),
                  iommu_support_is_set)]
    if arch == 'ARM64':
        l += [KconfigCheck('self_protection', 'defconfig', 'ARM64_PAN', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'ARM64_EPAN', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'UNMAP_KERNEL_AT_EL0', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'ARM64_E0PD', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'RODATA_FULL_DEFAULT_ENABLED', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'ARM64_PTR_AUTH_KERNEL', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'ARM64_BTI_KERNEL', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'MITIGATE_SPECTRE_BRANCH_HISTORY', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'ARM64_MTE', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'RANDOMIZE_MODULE_REGION_FULL', 'y')]
        l += [OR(KconfigCheck('self_protection', 'defconfig', 'HARDEN_EL2_VECTORS', 'y'),
                 AND(KconfigCheck('self_protection', 'defconfig', 'RANDOMIZE_BASE', 'y'),
                     VersionCheck((5, 9))))] # HARDEN_EL2_VECTORS was included in RANDOMIZE_BASE in v5.9
        l += [OR(KconfigCheck('self_protection', 'defconfig', 'HARDEN_BRANCH_PREDICTOR', 'y'),
                 VersionCheck((5, 10)))] # HARDEN_BRANCH_PREDICTOR is enabled by default since v5.10
    if arch == 'ARM':
        l += [KconfigCheck('self_protection', 'defconfig', 'CPU_SW_DOMAIN_PAN', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'HARDEN_BRANCH_PREDICTOR', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'HARDEN_BRANCH_HISTORY', 'y')]
        l += [KconfigCheck('self_protection', 'defconfig', 'DEBUG_ALIGN_RODATA', 'y')]

    # 'self_protection', 'kspp'
    l += [KconfigCheck('self_protection', 'kspp', 'BUG_ON_DATA_CORRUPTION', 'y')]
    l += [KconfigCheck('self_protection', 'kspp', 'SCHED_STACK_END_CHECK', 'y')]
    l += [KconfigCheck('self_protection', 'kspp', 'SLAB_FREELIST_HARDENED', 'y')]
    l += [KconfigCheck('self_protection', 'kspp', 'SLAB_FREELIST_RANDOM', 'y')]
    l += [KconfigCheck('self_protection', 'kspp', 'SHUFFLE_PAGE_ALLOCATOR', 'y')]
    l += [KconfigCheck('self_protection', 'kspp', 'FORTIFY_SOURCE', 'y')]
    l += [KconfigCheck('self_protection', 'kspp', 'DEBUG_LIST', 'y')]
    l += [KconfigCheck('self_protection', 'kspp', 'DEBUG_VIRTUAL', 'y')]
    l += [KconfigCheck('self_protection', 'kspp', 'DEBUG_SG', 'y')]
    l += [KconfigCheck('self_protection', 'kspp', 'DEBUG_CREDENTIALS', 'y')]
    l += [KconfigCheck('self_protection', 'kspp', 'DEBUG_NOTIFIERS', 'y')]
    l += [KconfigCheck('self_protection', 'kspp', 'INIT_ON_ALLOC_DEFAULT_ON', 'y')]
    l += [KconfigCheck('self_protection', 'kspp', 'KFENCE', 'y')]
    l += [KconfigCheck('self_protection', 'kspp', 'ZERO_CALL_USED_REGS', 'y')]
    l += [KconfigCheck('self_protection', 'kspp', 'HW_RANDOM_TPM', 'y')]
    l += [KconfigCheck('self_protection', 'kspp', 'STATIC_USERMODEHELPER', 'y')] # needs userspace support
    randstruct_is_set = OR(KconfigCheck('self_protection', 'kspp', 'RANDSTRUCT_FULL', 'y'),
                           KconfigCheck('self_protection', 'kspp', 'GCC_PLUGIN_RANDSTRUCT', 'y'))
    l += [randstruct_is_set]
    l += [AND(KconfigCheck('self_protection', 'kspp', 'RANDSTRUCT_PERFORMANCE', 'is not set'),
              KconfigCheck('self_protection', 'kspp', 'GCC_PLUGIN_RANDSTRUCT_PERFORMANCE', 'is not set'),
              randstruct_is_set)]
    hardened_usercopy_is_set = KconfigCheck('self_protection', 'kspp', 'HARDENED_USERCOPY', 'y')
    l += [hardened_usercopy_is_set]
    l += [AND(KconfigCheck('self_protection', 'kspp', 'HARDENED_USERCOPY_FALLBACK', 'is not set'),
              hardened_usercopy_is_set)]
    l += [AND(KconfigCheck('self_protection', 'kspp', 'HARDENED_USERCOPY_PAGESPAN', 'is not set'),
              hardened_usercopy_is_set)]
    l += [AND(KconfigCheck('self_protection', 'kspp', 'GCC_PLUGIN_LATENT_ENTROPY', 'y'),
              gcc_plugins_support_is_set)]
    l += [OR(KconfigCheck('self_protection', 'kspp', 'MODULE_SIG', 'y'),
             modules_not_set)]
    l += [OR(KconfigCheck('self_protection', 'kspp', 'MODULE_SIG_ALL', 'y'),
             modules_not_set)]
    l += [OR(KconfigCheck('self_protection', 'kspp', 'MODULE_SIG_SHA512', 'y'),
             modules_not_set)]
    l += [OR(KconfigCheck('self_protection', 'kspp', 'MODULE_SIG_FORCE', 'y'),
             modules_not_set)] # refers to LOCKDOWN
    l += [OR(KconfigCheck('self_protection', 'kspp', 'INIT_STACK_ALL_ZERO', 'y'),
             KconfigCheck('self_protection', 'kspp', 'GCC_PLUGIN_STRUCTLEAK_BYREF_ALL', 'y'))]
    l += [OR(KconfigCheck('self_protection', 'kspp', 'INIT_ON_FREE_DEFAULT_ON', 'y'),
             KconfigCheck('self_protection', 'kspp', 'PAGE_POISONING_ZERO', 'y'))]
             # CONFIG_INIT_ON_FREE_DEFAULT_ON was added in v5.3.
             # CONFIG_PAGE_POISONING_ZERO was removed in v5.11.
             # Starting from v5.11 CONFIG_PAGE_POISONING unconditionally checks
             # the 0xAA poison pattern on allocation.
             # That brings higher performance penalty.
    l += [OR(KconfigCheck('self_protection', 'kspp', 'EFI_DISABLE_PCI_DMA', 'y'),
             efi_not_set)]
    l += [OR(KconfigCheck('self_protection', 'kspp', 'RESET_ATTACK_MITIGATION', 'y'),
             efi_not_set)] # needs userspace support (systemd)
    ubsan_bounds_is_set = KconfigCheck('self_protection', 'kspp', 'UBSAN_BOUNDS', 'y')
    l += [ubsan_bounds_is_set]
    l += [OR(KconfigCheck('self_protection', 'kspp', 'UBSAN_LOCAL_BOUNDS', 'y'),
             AND(ubsan_bounds_is_set,
                 cc_is_gcc))]
    l += [AND(KconfigCheck('self_protection', 'kspp', 'UBSAN_TRAP', 'y'),
              ubsan_bounds_is_set,
              KconfigCheck('self_protection', 'kspp', 'UBSAN_SHIFT', 'is not set'),
              KconfigCheck('self_protection', 'kspp', 'UBSAN_DIV_ZERO', 'is not set'),
              KconfigCheck('self_protection', 'kspp', 'UBSAN_UNREACHABLE', 'is not set'),
              KconfigCheck('self_protection', 'kspp', 'UBSAN_BOOL', 'is not set'),
              KconfigCheck('self_protection', 'kspp', 'UBSAN_ENUM', 'is not set'),
              KconfigCheck('self_protection', 'kspp', 'UBSAN_ALIGNMENT', 'is not set'))] # only array index bounds checking with traps
    if arch in ('X86_64', 'ARM64', 'X86_32'):
        l += [AND(KconfigCheck('self_protection', 'kspp', 'UBSAN_SANITIZE_ALL', 'y'),
                  ubsan_bounds_is_set)] # ARCH_HAS_UBSAN_SANITIZE_ALL is not enabled for ARM
        stackleak_is_set = KconfigCheck('self_protection', 'kspp', 'GCC_PLUGIN_STACKLEAK', 'y')
        l += [AND(stackleak_is_set, gcc_plugins_support_is_set)]
        l += [AND(KconfigCheck('self_protection', 'kspp', 'STACKLEAK_METRICS', 'is not set'),
                  stackleak_is_set,
                  gcc_plugins_support_is_set)]
        l += [AND(KconfigCheck('self_protection', 'kspp', 'STACKLEAK_RUNTIME_DISABLE', 'is not set'),
                  stackleak_is_set,
                  gcc_plugins_support_is_set)]
        l += [KconfigCheck('self_protection', 'kspp', 'RANDOMIZE_KSTACK_OFFSET_DEFAULT', 'y')]
    if arch in ('X86_64', 'ARM64'):
        cfi_clang_is_set = KconfigCheck('self_protection', 'kspp', 'CFI_CLANG', 'y')
        l += [cfi_clang_is_set]
        l += [AND(KconfigCheck('self_protection', 'kspp', 'CFI_PERMISSIVE', 'is not set'),
                  cfi_clang_is_set)]
    if arch in ('X86_64', 'X86_32'):
        l += [KconfigCheck('self_protection', 'kspp', 'SCHED_CORE', 'y')]
        l += [KconfigCheck('self_protection', 'kspp', 'DEFAULT_MMAP_MIN_ADDR', '65536')]
        l += [KconfigCheck('self_protection', 'kspp', 'IOMMU_DEFAULT_DMA_STRICT', 'y')]
        l += [KconfigCheck('self_protection', 'kspp', 'IOMMU_DEFAULT_PASSTHROUGH', 'is not set')] # true if IOMMU_DEFAULT_DMA_STRICT is set
        l += [AND(KconfigCheck('self_protection', 'kspp', 'INTEL_IOMMU_DEFAULT_ON', 'y'),
                  iommu_support_is_set)]
    if arch in ('ARM64', 'ARM'):
        l += [KconfigCheck('self_protection', 'kspp', 'DEBUG_WX', 'y')]
        l += [KconfigCheck('self_protection', 'kspp', 'WERROR', 'y')]
        l += [KconfigCheck('self_protection', 'kspp', 'DEFAULT_MMAP_MIN_ADDR', '32768')]
        l += [KconfigCheck('self_protection', 'kspp', 'SYN_COOKIES', 'y')] # another reason?
    if arch == 'X86_64':
        l += [KconfigCheck('self_protection', 'kspp', 'SLS', 'y')] # vs CVE-2021-26341 in Straight-Line-Speculation
        l += [AND(KconfigCheck('self_protection', 'kspp', 'INTEL_IOMMU_SVM', 'y'),
                  iommu_support_is_set)]
        l += [AND(KconfigCheck('self_protection', 'kspp', 'AMD_IOMMU_V2', 'y'),
                  iommu_support_is_set)]
    if arch == 'ARM64':
        l += [KconfigCheck('self_protection', 'kspp', 'ARM64_SW_TTBR0_PAN', 'y')]
        l += [KconfigCheck('self_protection', 'kspp', 'SHADOW_CALL_STACK', 'y')]
        l += [KconfigCheck('self_protection', 'kspp', 'KASAN_HW_TAGS', 'y')] # see also: kasan=on, kasan.stacktrace=off, kasan.fault=panic
    if arch == 'X86_32':
        l += [KconfigCheck('self_protection', 'kspp', 'PAGE_TABLE_ISOLATION', 'y')]
        l += [KconfigCheck('self_protection', 'kspp', 'HIGHMEM64G', 'y')]
        l += [KconfigCheck('self_protection', 'kspp', 'X86_PAE', 'y')]
        l += [AND(KconfigCheck('self_protection', 'kspp', 'INTEL_IOMMU', 'y'),
                  iommu_support_is_set)]

    # 'self_protection', 'clipos'
    l += [KconfigCheck('self_protection', 'clipos', 'SLAB_MERGE_DEFAULT', 'is not set')]

    # 'security_policy'
    if arch in ('X86_64', 'ARM64', 'X86_32'):
        l += [KconfigCheck('security_policy', 'defconfig', 'SECURITY', 'y')] # and choose your favourite LSM
    if arch == 'ARM':
        l += [KconfigCheck('security_policy', 'kspp', 'SECURITY', 'y')] # and choose your favourite LSM
    l += [KconfigCheck('security_policy', 'kspp', 'SECURITY_YAMA', 'y')]
    l += [KconfigCheck('security_policy', 'kspp', 'SECURITY_LANDLOCK', 'y')]
    l += [KconfigCheck('security_policy', 'kspp', 'SECURITY_SELINUX_DISABLE', 'is not set')]
    l += [KconfigCheck('security_policy', 'kspp', 'SECURITY_SELINUX_BOOTPARAM', 'is not set')]
    l += [KconfigCheck('security_policy', 'kspp', 'SECURITY_SELINUX_DEVELOP', 'is not set')]
    l += [KconfigCheck('security_policy', 'kspp', 'SECURITY_LOCKDOWN_LSM', 'y')]
    l += [KconfigCheck('security_policy', 'kspp', 'SECURITY_LOCKDOWN_LSM_EARLY', 'y')]
    l += [KconfigCheck('security_policy', 'kspp', 'LOCK_DOWN_KERNEL_FORCE_CONFIDENTIALITY', 'y')]
    l += [KconfigCheck('security_policy', 'kspp', 'SECURITY_WRITABLE_HOOKS', 'is not set')] # refers to SECURITY_SELINUX_DISABLE

    # 'cut_attack_surface', 'defconfig'
    l += [KconfigCheck('cut_attack_surface', 'defconfig', 'SECCOMP', 'y')]
    l += [KconfigCheck('cut_attack_surface', 'defconfig', 'SECCOMP_FILTER', 'y')]
    l += [OR(KconfigCheck('cut_attack_surface', 'defconfig', 'BPF_UNPRIV_DEFAULT_OFF', 'y'),
             bpf_syscall_not_set)] # see unprivileged_bpf_disabled
    if arch in ('X86_64', 'ARM64', 'X86_32'):
        l += [OR(KconfigCheck('cut_attack_surface', 'defconfig', 'STRICT_DEVMEM', 'y'),
                 devmem_not_set)] # refers to LOCKDOWN
    if arch in ('X86_64', 'X86_32'):
        l += [KconfigCheck('cut_attack_surface', 'defconfig', 'X86_INTEL_TSX_MODE_OFF', 'y')] # tsx=off

    # 'cut_attack_surface', 'kspp'
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'SECURITY_DMESG_RESTRICT', 'y')]
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'ACPI_CUSTOM_METHOD', 'is not set')] # refers to LOCKDOWN
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'COMPAT_BRK', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'DEVKMEM', 'is not set')] # refers to LOCKDOWN
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'COMPAT_VDSO', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'BINFMT_MISC', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'INET_DIAG', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'KEXEC', 'is not set')] # refers to LOCKDOWN
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'PROC_KCORE', 'is not set')] # refers to LOCKDOWN
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'LEGACY_PTYS', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'HIBERNATION', 'is not set')] # refers to LOCKDOWN
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'COMPAT', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'IA32_EMULATION', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'X86_X32', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'X86_X32_ABI', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'MODIFY_LDT_SYSCALL', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'OABI_COMPAT', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'kspp', 'X86_MSR', 'is not set')] # refers to LOCKDOWN
    l += [modules_not_set]
    l += [devmem_not_set]
    l += [OR(KconfigCheck('cut_attack_surface', 'kspp', 'IO_STRICT_DEVMEM', 'y'),
             devmem_not_set)] # refers to LOCKDOWN
    l += [AND(KconfigCheck('cut_attack_surface', 'kspp', 'LDISC_AUTOLOAD', 'is not set'),
              KconfigCheck('cut_attack_surface', 'kspp', 'LDISC_AUTOLOAD', 'is present'))]
    if arch == 'X86_64':
        l += [KconfigCheck('cut_attack_surface', 'kspp', 'LEGACY_VSYSCALL_NONE', 'y')] # 'vsyscall=none'
    if arch == 'ARM':
        l += [OR(KconfigCheck('cut_attack_surface', 'kspp', 'STRICT_DEVMEM', 'y'),
                 devmem_not_set)] # refers to LOCKDOWN

    # 'cut_attack_surface', 'grsec'
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'ZSMALLOC_STAT', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'PAGE_OWNER', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'DEBUG_KMEMLEAK', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'BINFMT_AOUT', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'KPROBE_EVENTS', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'UPROBE_EVENTS', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'GENERIC_TRACER', 'is not set')] # refers to LOCKDOWN
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'FUNCTION_TRACER', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'STACK_TRACER', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'HIST_TRIGGERS', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'BLK_DEV_IO_TRACE', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'PROC_VMCORE', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'PROC_PAGE_MONITOR', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'USELIB', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'CHECKPOINT_RESTORE', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'USERFAULTFD', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'HWPOISON_INJECT', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'MEM_SOFT_DIRTY', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'DEVPORT', 'is not set')] # refers to LOCKDOWN
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'DEBUG_FS', 'is not set')] # refers to LOCKDOWN
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'NOTIFIER_ERROR_INJECTION', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'FAIL_FUTEX', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'PUNIT_ATOM_DEBUG', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'ACPI_CONFIGFS', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'EDAC_DEBUG', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'DRM_I915_DEBUG', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'BCACHE_CLOSURES_DEBUG', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'DVB_C8SECTPFE', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'MTD_SLRAM', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'MTD_PHRAM', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'IO_URING', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'KCMP', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'RSEQ', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'LATENCYTOP', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'KCOV', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'PROVIDE_OHCI1394_DMA_INIT', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'grsec', 'SUNRPC_DEBUG', 'is not set')]
    l += [AND(KconfigCheck('cut_attack_surface', 'grsec', 'PTDUMP_DEBUGFS', 'is not set'),
              KconfigCheck('cut_attack_surface', 'grsec', 'X86_PTDUMP', 'is not set'))]

    # 'cut_attack_surface', 'maintainer'
    l += [KconfigCheck('cut_attack_surface', 'maintainer', 'DRM_LEGACY', 'is not set')] # recommended by Daniel Vetter in /issues/38
    l += [KconfigCheck('cut_attack_surface', 'maintainer', 'FB', 'is not set')] # recommended by Daniel Vetter in /issues/38
    l += [KconfigCheck('cut_attack_surface', 'maintainer', 'VT', 'is not set')] # recommended by Daniel Vetter in /issues/38
    l += [KconfigCheck('cut_attack_surface', 'maintainer', 'BLK_DEV_FD', 'is not set')] # recommended by Denis Efremov in /pull/54
    l += [KconfigCheck('cut_attack_surface', 'maintainer', 'BLK_DEV_FD_RAWCMD', 'is not set')] # recommended by Denis Efremov in /pull/62
    l += [KconfigCheck('cut_attack_surface', 'maintainer', 'NOUVEAU_LEGACY_CTX_SUPPORT', 'is not set')]
                                            # recommended by Dave Airlie in kernel commit b30a43ac7132cdda

    # 'cut_attack_surface', 'clipos'
    l += [KconfigCheck('cut_attack_surface', 'clipos', 'STAGING', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'clipos', 'KSM', 'is not set')] # to prevent FLUSH+RELOAD attack
    l += [KconfigCheck('cut_attack_surface', 'clipos', 'KALLSYMS', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'clipos', 'X86_VSYSCALL_EMULATION', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'clipos', 'MAGIC_SYSRQ', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'clipos', 'KEXEC_FILE', 'is not set')] # refers to LOCKDOWN (permissive)
    l += [KconfigCheck('cut_attack_surface', 'clipos', 'USER_NS', 'is not set')] # user.max_user_namespaces=0
    l += [KconfigCheck('cut_attack_surface', 'clipos', 'X86_CPUID', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'clipos', 'X86_IOPL_IOPERM', 'is not set')] # refers to LOCKDOWN
    l += [KconfigCheck('cut_attack_surface', 'clipos', 'ACPI_TABLE_UPGRADE', 'is not set')] # refers to LOCKDOWN
    l += [KconfigCheck('cut_attack_surface', 'clipos', 'EFI_CUSTOM_SSDT_OVERLAYS', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'clipos', 'COREDUMP', 'is not set')] # cut userspace attack surface
#   l += [KconfigCheck('cut_attack_surface', 'clipos', 'IKCONFIG', 'is not set')] # no, IKCONFIG is needed for this check :)

    # 'cut_attack_surface', 'lockdown'
    l += [KconfigCheck('cut_attack_surface', 'lockdown', 'EFI_TEST', 'is not set')] # refers to LOCKDOWN
    l += [KconfigCheck('cut_attack_surface', 'lockdown', 'MMIOTRACE_TEST', 'is not set')] # refers to LOCKDOWN
    l += [KconfigCheck('cut_attack_surface', 'lockdown', 'KPROBES', 'is not set')] # refers to LOCKDOWN
    l += [bpf_syscall_not_set] # refers to LOCKDOWN

    # 'cut_attack_surface', 'my'
    l += [KconfigCheck('cut_attack_surface', 'my', 'LEGACY_TIOCSTI', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'my', 'MMIOTRACE', 'is not set')] # refers to LOCKDOWN (permissive)
    l += [KconfigCheck('cut_attack_surface', 'my', 'LIVEPATCH', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'my', 'IP_DCCP', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'my', 'IP_SCTP', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'my', 'FTRACE', 'is not set')] # refers to LOCKDOWN
    l += [KconfigCheck('cut_attack_surface', 'my', 'VIDEO_VIVID', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'my', 'INPUT_EVBUG', 'is not set')] # Can be used as a keylogger
    l += [KconfigCheck('cut_attack_surface', 'my', 'KGDB', 'is not set')]
    l += [KconfigCheck('cut_attack_surface', 'my', 'AIO', 'is not set')]
    l += [OR(KconfigCheck('cut_attack_surface', 'my', 'TRIM_UNUSED_KSYMS', 'y'),
             modules_not_set)]

    # 'harden_userspace'
    if arch == 'ARM64':
        l += [KconfigCheck('harden_userspace', 'defconfig', 'ARM64_PTR_AUTH', 'y')]
        l += [KconfigCheck('harden_userspace', 'defconfig', 'ARM64_BTI', 'y')]
    if arch in ('ARM', 'X86_32'):
        l += [KconfigCheck('harden_userspace', 'defconfig', 'VMSPLIT_3G', 'y')]
    if arch in ('X86_64', 'ARM64'):
        l += [KconfigCheck('harden_userspace', 'clipos', 'ARCH_MMAP_RND_BITS', '32')]
    if arch in ('X86_32', 'ARM'):
        l += [KconfigCheck('harden_userspace', 'my', 'ARCH_MMAP_RND_BITS', '16')]


def add_cmdline_checks(l, arch):
    # Calling the CmdlineCheck class constructor:
    #     CmdlineCheck(reason, decision, name, expected)
    #
    # [!] Don't add CmdlineChecks in add_kconfig_checks() to avoid wrong results
    #     when the tool doesn't check the cmdline.
    #
    # [!] Make sure that values of the options in CmdlineChecks need normalization.
    #     For more info see normalize_cmdline_options().
    #
    # A common pattern for checking the 'param_x' cmdline parameter
    # that __overrides__ the 'PARAM_X_DEFAULT' kconfig option:
    #   l += [OR(CmdlineCheck(reason, decision, 'param_x', '1'),
    #            AND(KconfigCheck(reason, decision, 'PARAM_X_DEFAULT_ON', 'y'),
    #                CmdlineCheck(reason, decision, 'param_x, 'is not set')))]
    #
    # Here we don't check the kconfig options or minimal kernel version
    # required for the cmdline parameters. That would make the checks
    # very complex and not give a 100% guarantee anyway.

    # 'self_protection', 'defconfig'
    l += [CmdlineCheck('self_protection', 'defconfig', 'nosmep', 'is not set')]
    l += [CmdlineCheck('self_protection', 'defconfig', 'nosmap', 'is not set')]
    l += [CmdlineCheck('self_protection', 'defconfig', 'nokaslr', 'is not set')]
    l += [CmdlineCheck('self_protection', 'defconfig', 'nopti', 'is not set')]
    l += [CmdlineCheck('self_protection', 'defconfig', 'nospectre_v1', 'is not set')]
    l += [CmdlineCheck('self_protection', 'defconfig', 'nospectre_v2', 'is not set')]
    l += [CmdlineCheck('self_protection', 'defconfig', 'nospectre_bhb', 'is not set')]
    l += [CmdlineCheck('self_protection', 'defconfig', 'nospec_store_bypass_disable', 'is not set')]
    l += [CmdlineCheck('self_protection', 'defconfig', 'arm64.nobti', 'is not set')]
    l += [CmdlineCheck('self_protection', 'defconfig', 'arm64.nopauth', 'is not set')]
    l += [CmdlineCheck('self_protection', 'defconfig', 'arm64.nomte', 'is not set')]
    l += [OR(CmdlineCheck('self_protection', 'defconfig', 'spectre_v2', 'is not off'),
             AND(CmdlineCheck('self_protection', 'kspp', 'mitigations', 'auto,nosmt'),
                 CmdlineCheck('self_protection', 'defconfig', 'spectre_v2', 'is not set')))]
    l += [OR(CmdlineCheck('self_protection', 'defconfig', 'spectre_v2_user', 'is not off'),
             AND(CmdlineCheck('self_protection', 'kspp', 'mitigations', 'auto,nosmt'),
                 CmdlineCheck('self_protection', 'defconfig', 'spectre_v2_user', 'is not set')))]
    l += [OR(CmdlineCheck('self_protection', 'defconfig', 'spec_store_bypass_disable', 'is not off'),
             AND(CmdlineCheck('self_protection', 'kspp', 'mitigations', 'auto,nosmt'),
                 CmdlineCheck('self_protection', 'defconfig', 'spec_store_bypass_disable', 'is not set')))]
    l += [OR(CmdlineCheck('self_protection', 'defconfig', 'l1tf', 'is not off'),
             AND(CmdlineCheck('self_protection', 'kspp', 'mitigations', 'auto,nosmt'),
                 CmdlineCheck('self_protection', 'defconfig', 'l1tf', 'is not set')))]
    l += [OR(CmdlineCheck('self_protection', 'defconfig', 'mds', 'is not off'),
             AND(CmdlineCheck('self_protection', 'kspp', 'mitigations', 'auto,nosmt'),
                 CmdlineCheck('self_protection', 'defconfig', 'mds', 'is not set')))]
    l += [OR(CmdlineCheck('self_protection', 'defconfig', 'tsx_async_abort', 'is not off'),
             AND(CmdlineCheck('self_protection', 'kspp', 'mitigations', 'auto,nosmt'),
                 CmdlineCheck('self_protection', 'defconfig', 'tsx_async_abort', 'is not set')))]
    l += [OR(CmdlineCheck('self_protection', 'defconfig', 'srbds', 'is not off'),
             AND(CmdlineCheck('self_protection', 'kspp', 'mitigations', 'auto,nosmt'),
                 CmdlineCheck('self_protection', 'defconfig', 'srbds', 'is not set')))]
    l += [OR(CmdlineCheck('self_protection', 'defconfig', 'mmio_stale_data', 'is not off'),
             AND(CmdlineCheck('self_protection', 'kspp', 'mitigations', 'auto,nosmt'),
                 CmdlineCheck('self_protection', 'defconfig', 'mmio_stale_data', 'is not set')))]
    l += [OR(CmdlineCheck('self_protection', 'defconfig', 'retbleed', 'is not off'),
             AND(CmdlineCheck('self_protection', 'kspp', 'mitigations', 'auto,nosmt'),
                 CmdlineCheck('self_protection', 'defconfig', 'retbleed', 'is not set')))]
    l += [OR(CmdlineCheck('self_protection', 'defconfig', 'kpti', 'is not off'),
             AND(CmdlineCheck('self_protection', 'kspp', 'mitigations', 'auto,nosmt'),
                 CmdlineCheck('self_protection', 'defconfig', 'kpti', 'is not set')))]
    if arch == 'ARM64':
        l += [OR(CmdlineCheck('self_protection', 'defconfig', 'ssbd', 'kernel'),
                 CmdlineCheck('self_protection', 'my', 'ssbd', 'force-on'),
                 AND(CmdlineCheck('self_protection', 'kspp', 'mitigations', 'auto,nosmt'),
                     CmdlineCheck('self_protection', 'defconfig', 'ssbd', 'is not set')))]
        l += [OR(CmdlineCheck('self_protection', 'defconfig', 'rodata', 'full'),
                 AND(KconfigCheck('self_protection', 'defconfig', 'RODATA_FULL_DEFAULT_ENABLED', 'y'),
                     CmdlineCheck('self_protection', 'defconfig', 'rodata', 'is not set')))]
    else:
        l += [OR(CmdlineCheck('self_protection', 'defconfig', 'rodata', '1'),
                 CmdlineCheck('self_protection', 'defconfig', 'rodata', 'is not set'))]

    # 'self_protection', 'kspp'
    l += [CmdlineCheck('self_protection', 'kspp', 'nosmt', 'is present')]
    l += [CmdlineCheck('self_protection', 'kspp', 'mitigations', 'auto,nosmt')] # 'nosmt' by kspp + 'auto' by defconfig
    l += [CmdlineCheck('self_protection', 'kspp', 'slab_merge', 'is not set')] # consequence of 'slab_nomerge' by kspp
    l += [CmdlineCheck('self_protection', 'kspp', 'slub_merge', 'is not set')] # consequence of 'slab_nomerge' by kspp
    l += [OR(CmdlineCheck('self_protection', 'kspp', 'slab_nomerge', 'is present'),
             AND(KconfigCheck('self_protection', 'clipos', 'SLAB_MERGE_DEFAULT', 'is not set'),
                 CmdlineCheck('self_protection', 'kspp', 'slab_merge', 'is not set'),
                 CmdlineCheck('self_protection', 'kspp', 'slub_merge', 'is not set')))]
    l += [OR(CmdlineCheck('self_protection', 'kspp', 'init_on_alloc', '1'),
             AND(KconfigCheck('self_protection', 'kspp', 'INIT_ON_ALLOC_DEFAULT_ON', 'y'),
                 CmdlineCheck('self_protection', 'kspp', 'init_on_alloc', 'is not set')))]
    l += [OR(CmdlineCheck('self_protection', 'kspp', 'init_on_free', '1'),
             AND(KconfigCheck('self_protection', 'kspp', 'INIT_ON_FREE_DEFAULT_ON', 'y'),
                 CmdlineCheck('self_protection', 'kspp', 'init_on_free', 'is not set')),
             AND(CmdlineCheck('self_protection', 'kspp', 'page_poison', '1'),
                 KconfigCheck('self_protection', 'kspp', 'PAGE_POISONING_ZERO', 'y'),
                 CmdlineCheck('self_protection', 'kspp', 'slub_debug', 'P')))]
    l += [OR(CmdlineCheck('self_protection', 'kspp', 'iommu.strict', '1'),
             AND(KconfigCheck('self_protection', 'kspp', 'IOMMU_DEFAULT_DMA_STRICT', 'y'),
                 CmdlineCheck('self_protection', 'kspp', 'iommu.strict', 'is not set')))]
    l += [OR(CmdlineCheck('self_protection', 'kspp', 'iommu.passthrough', '0'),
             AND(KconfigCheck('self_protection', 'kspp', 'IOMMU_DEFAULT_PASSTHROUGH', 'is not set'),
                 CmdlineCheck('self_protection', 'kspp', 'iommu.passthrough', 'is not set')))]
    # The cmdline checks compatible with the kconfig recommendations of the KSPP project...
    l += [OR(CmdlineCheck('self_protection', 'kspp', 'hardened_usercopy', '1'),
             AND(KconfigCheck('self_protection', 'kspp', 'HARDENED_USERCOPY', 'y'),
                 CmdlineCheck('self_protection', 'kspp', 'hardened_usercopy', 'is not set')))]
    l += [OR(CmdlineCheck('self_protection', 'kspp', 'slab_common.usercopy_fallback', '0'),
             AND(KconfigCheck('self_protection', 'kspp', 'HARDENED_USERCOPY_FALLBACK', 'is not set'),
                 CmdlineCheck('self_protection', 'kspp', 'slab_common.usercopy_fallback', 'is not set')))]
    # ... the end
    if arch in ('X86_64', 'ARM64', 'X86_32'):
        l += [OR(CmdlineCheck('self_protection', 'kspp', 'randomize_kstack_offset', '1'),
                 AND(KconfigCheck('self_protection', 'kspp', 'RANDOMIZE_KSTACK_OFFSET_DEFAULT', 'y'),
                     CmdlineCheck('self_protection', 'kspp', 'randomize_kstack_offset', 'is not set')))]
    if arch in ('X86_64', 'X86_32'):
        l += [AND(CmdlineCheck('self_protection', 'kspp', 'pti', 'on'),
                  CmdlineCheck('self_protection', 'defconfig', 'nopti', 'is not set'))]

    # 'self_protection', 'clipos'
    l += [CmdlineCheck('self_protection', 'clipos', 'page_alloc.shuffle', '1')]
    if arch in ('X86_64', 'X86_32'):
        l += [CmdlineCheck('self_protection', 'clipos', 'iommu', 'force')]

    # 'cut_attack_surface', 'defconfig'
    if arch in ('X86_64', 'X86_32'):
        l += [OR(CmdlineCheck('cut_attack_surface', 'defconfig', 'tsx', 'off'),
                 AND(KconfigCheck('cut_attack_surface', 'defconfig', 'X86_INTEL_TSX_MODE_OFF', 'y'),
                     CmdlineCheck('cut_attack_surface', 'defconfig', 'tsx', 'is not set')))]

    # 'cut_attack_surface', 'kspp'
    if arch == 'X86_64':
        l += [OR(CmdlineCheck('cut_attack_surface', 'kspp', 'vsyscall', 'none'),
                 AND(KconfigCheck('cut_attack_surface', 'kspp', 'LEGACY_VSYSCALL_NONE', 'y'),
                     CmdlineCheck('cut_attack_surface', 'kspp', 'vsyscall', 'is not set')))]

    # 'cut_attack_surface', 'grsec'
    # The cmdline checks compatible with the kconfig options disabled by grsecurity...
    l += [OR(CmdlineCheck('cut_attack_surface', 'grsec', 'debugfs', 'off'),
             KconfigCheck('cut_attack_surface', 'grsec', 'DEBUG_FS', 'is not set'))] # ... the end

    # 'cut_attack_surface', 'my'
    l += [CmdlineCheck('cut_attack_surface', 'my', 'sysrq_always_enabled', 'is not set')]


no_kstrtobool_options = [
    'debugfs', # See debugfs_kernel() in fs/debugfs/inode.c
    'mitigations', # See mitigations_parse_cmdline() in kernel/cpu.c
    'pti', # See pti_check_boottime_disable() in arch/x86/mm/pti.c
    'spectre_v2', # See spectre_v2_parse_cmdline() in arch/x86/kernel/cpu/bugs.c
    'spectre_v2_user', # See spectre_v2_parse_user_cmdline() in arch/x86/kernel/cpu/bugs.c
    'spec_store_bypass_disable', # See ssb_parse_cmdline() in arch/x86/kernel/cpu/bugs.c
    'l1tf', # See l1tf_cmdline() in arch/x86/kernel/cpu/bugs.c
    'mds', # See mds_cmdline() in arch/x86/kernel/cpu/bugs.c
    'tsx_async_abort', # See tsx_async_abort_parse_cmdline() in arch/x86/kernel/cpu/bugs.c
    'srbds', # See srbds_parse_cmdline() in arch/x86/kernel/cpu/bugs.c
    'mmio_stale_data', # See mmio_stale_data_parse_cmdline() in arch/x86/kernel/cpu/bugs.c
    'retbleed', # See retbleed_parse_cmdline() in arch/x86/kernel/cpu/bugs.c
    'tsx' # See tsx_init() in arch/x86/kernel/cpu/tsx.c
]


def normalize_cmdline_options(option, value):
    # Don't normalize the cmdline option values if
    # the Linux kernel doesn't use kstrtobool() for them
    if option in no_kstrtobool_options:
        return value

    # Implement a limited part of the kstrtobool() logic
    if value in ('1', 'on', 'On', 'ON', 'y', 'Y', 'yes', 'Yes', 'YES'):
        return '1'
    if value in ('0', 'off', 'Off', 'OFF', 'n', 'N', 'no', 'No', 'NO'):
        return '0'

    # Preserve unique values
    return value
