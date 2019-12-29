import sys
# https://github.com/eliben/pyelftools
from elftools.elf.elffile import ELFFile, ELFError


def is_fn(DIE):
    return DIE.tag == 'DW_TAG_subprogram'


def is_var(DIE):
    return DIE.tag == 'DW_TAG_variable'


def is_struct(DIE):
    return DIE.tag == 'DW_TAG_structure_type'


def is_base_type(DIE):
    return DIE.tag == 'DW_TAG_base_type'


def is_ptr(DIE):
    return DIE.tag == 'DW_TAG_pointer_type'


def is_inlined(DIE):
    return DIE.tag == 'DW_TAG_inlined_subroutine'


def get_name(DIE):
    if 'DW_AT_name' in DIE.attributes:
        return DIE.attributes['DW_AT_name'].value.decode('UTF-8')
    else:
        return ''


def get_type_value(DIE):
    if 'DW_AT_type' in DIE.attributes:
        return DIE.attributes['DW_AT_type'].value
    else:
        return 0


def get_byte_size(DIE):
    if 'DW_AT_byte_size' in DIE.attributes:
        return DIE.attributes['DW_AT_byte_size'].value
    else:
        return 0


def is_abstract(DIE):
    return 'DW_AT_abstract_origin' in DIE.attributes


def is_fn_named(DIE, fn_name):
    return get_name(DIE) == fn_name


def is_dw_fn(DIE, fn_name):
    return is_fn(DIE) and is_fn_named(DIE, fn_name)


def find_type_info(dwarf_info, value):
    for CU in dwarf_info.iter_CUs():
        for DIE in CU.iter_DIEs():
            if value == DIE.offset:
                return DIE


def print_var(dwarf_info, DIE):
    # print(DIE)
    if is_abstract(DIE):
        type_value = DIE.attributes['DW_AT_abstract_origin'].value
        ti = find_type_info(dwarf_info, type_value)
        print_var(dwarf_info, ti)
        return
    type_value = get_type_value(DIE)
    type_info = find_type_info(dwarf_info, type_value)
    # TODO: recurse ptr and const types
    if is_struct(type_info):
        print('\t%d\tstruct %s\t%s' %
              (get_byte_size(type_info), get_name(type_info), get_name(DIE)))
    elif is_base_type(type_info):
        print('\t%d\t%s\t%s' %
              (get_byte_size(type_info), get_name(type_info), get_name(DIE)))
    elif is_ptr(type_info):
        # print(type_info)
        pointed_to_type = find_type_info(dwarf_info, get_type_value(type_info))
        # print(pointed_to_type)
        # TODO: get ptr size?
        print('\t%d\t%s*\t%s' % (8, get_name(pointed_to_type), get_name(DIE)))
    else:
        print('\t%s' % get_name(DIE))
        print_type_info(type_info)


def parse_file(dwarf_info, fn_name):
    found_fn_name = False
    for CU in dwarf_info.iter_CUs():
        for DIE in CU.iter_DIEs():
            if found_fn_name:
                if is_fn(DIE):
                    return
                elif is_var(DIE):
                    print_var(dwarf_info, DIE)
                elif is_inlined(DIE):
                    type_value = DIE.attributes['DW_AT_abstract_origin'].value
                    ti = find_type_info(dwarf_info, type_value)
                    parse_file(dwarf_info, get_name(ti))
                # else:
                    # print(DIE)
            elif is_dw_fn(DIE, fn_name):
                found_fn_name = True
                print('%s:' % get_name(DIE))


if __name__ == '__main__':
    if len(sys.argv) == 3:
        with open(sys.argv[1], 'rb') as f:
            try:
                elffile = ELFFile(f)
                if not elffile.has_dwarf_info:
                    print('No dwarf info found in %s' % sys.argv[1])
                    sys.exit(1)
                parse_file(elffile.get_dwarf_info(), sys.argv[2])
            except ELFError as e:
                print('failed to parse elf: %s' % e)
                sys.exit(1)
    else:
        print('Usage: python frame_larger_than.py <file> <function>')
        sys.exit(1)
