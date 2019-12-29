readelf --debug-dump=info kvm.o

# Frame Larger Than
A python script to help debug `-Wframe-larger-than=` warnings.

## Example

```sh
$  make CC=clang arch/x86/kernel/kvm.o CFLAGS=-Wframe-larger-than=1000
...
arch/x86/kernel/kvm.c:494:13: warning: stack frame size of 1064 bytes in function 'kvm_send_ipi_mask_allbutself' [-Wframe-larger-than=]
static void kvm_send_ipi_mask_allbutself(const struct cpumask *mask, int vector)
            ^
$ python3 frame_larger_than.py arch/x86/kernel/kvm.o kvm_send_ipi_mask_allbutself
kvm_send_ipi_mask_allbutself:
        1024    struct cpumask  new_mask
        4       unsigned int    this_cpu
        8       *       local_mask
        4       int     pscr_ret__
        4       int     pfo_ret__
cpumask_copy:
bitmap_copy:
        4       unsigned int    len
        4       unsigned int    len
cpumask_clear_cpu:
clear_bit:
arch_clear_bit:
```

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
