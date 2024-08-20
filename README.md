# Frame Larger Than
A python script to help debug `-Wframe-larger-than=` warnings.

## Example

Build an object file, such as with the Linux kernel.

```sh
$  make CC=clang arch/x86/kernel/kvm.o CFLAGS=-Wframe-larger-than=1000
...
arch/x86/kernel/kvm.c:494:13: warning: stack frame size of 1064 bytes in function 'kvm_send_ipi_mask_allbutself' [-Wframe-larger-than=]
static void kvm_send_ipi_mask_allbutself(const struct cpumask *mask, int vector)
            ^
```

Run `frame_larger_than.py` on that object file with the function name that triggers the warning to see the function's stack usage.

```sh
$ frame_larger_than.py arch/x86/kernel/kvm.o kvm_send_ipi_mask_allbutself
kvm_send_ipi_mask_allbutself:
        1024    struct cpumask          new_mask
        4       unsigned int            this_cpu
        8       const struct cpumask*   local_mask
        4       int                     pscr_ret__
        4       int                     pfo_ret__
cpumask_copy:
bitmap_copy:
        4       unsigned int            len
        4       unsigned int            len
cpumask_clear_cpu:
clear_bit:
arch_clear_bit:
```

A little bit friendlier than trying to understand `llvm-dwarfdump *.o` or
`readelf --debug-dump=info *.o`.

## Dependencies
- [pyelftools](https://github.com/eliben/pyelftools)
```sh
$ sudo -H pip3 install pyelftools
```

## Formatting
```sh
$ pip3 install pyformat
$ pyformat --in-place frame_larger_than.py
```
