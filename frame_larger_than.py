#!/usr/bin/env python3

import sys
from functools import lru_cache
# https://github.com/eliben/pyelftools
from elftools.elf.elffile import ELFFile, ELFError
from elftools.dwarf.locationlists import LocationParser, LocationExpr
from elftools.dwarf.dwarf_expr import DWARFExprParser
from elftools.dwarf.descriptions import describe_reg_name


def is_fn(DIE):
    return DIE.tag == 'DW_TAG_subprogram'


def is_var(DIE):
    return DIE.tag == 'DW_TAG_variable'


def is_struct(DIE):
    return DIE.tag == 'DW_TAG_structure_type'


def is_union(DIE):
    return DIE.tag == 'DW_TAG_union_type'


def is_base_type(DIE):
    return DIE.tag == 'DW_TAG_base_type'


def is_ptr(DIE):
    return DIE.tag == 'DW_TAG_pointer_type'


def is_inlined(DIE):
    return DIE.tag == 'DW_TAG_inlined_subroutine'


def is_const(DIE):
    return DIE.tag == 'DW_TAG_const_type'


def is_array(DIE):
    return DIE.tag == 'DW_TAG_array_type'


def is_subrange(DIE):
    return DIE.tag == 'DW_TAG_subrange_type'


def is_typedef(DIE):
    return DIE.tag == 'DW_TAG_typedef'


def is_enum(DIE):
    return DIE.tag == 'DW_TAG_enumeration_type'


def get_name(DIE):
    if 'DW_AT_name' in DIE.attributes:
        return DIE.attributes['DW_AT_name'].value.decode('UTF-8')
    else:
        return '{anonymous}'


def get_type_value(DIE):
    if 'DW_AT_type' in DIE.attributes:
        return DIE.attributes['DW_AT_type'].value
    else:
        return 0


def get_array_count(DIE):
    if DIE.has_children:
        for child in DIE.iter_children():
            if is_subrange(child):
                return child.attributes['DW_AT_count'].value
    return 0


def get_byte_size(dwarf_info, DIE):
    if 'DW_AT_byte_size' in DIE.attributes:
        return DIE.attributes['DW_AT_byte_size'].value
    elif is_ptr(DIE):
        return dwarf_info.config.default_address_size
    elif is_typedef(DIE) or is_const(DIE):
        actual_type = find_type_info(dwarf_info, get_type_value(DIE))
        return get_byte_size(dwarf_info, actual_type)
    elif is_array(DIE):
        num_elements = get_array_count(DIE)
        pointed_to_type = find_type_info(dwarf_info, get_type_value(DIE))
        return get_byte_size(dwarf_info, pointed_to_type) * num_elements
    else:
        return 0


def is_abstract(DIE):
    return 'DW_AT_abstract_origin' in DIE.attributes


def is_fn_named(DIE, fn_name):
    return get_name(DIE) == fn_name


def is_dw_fn(DIE, fn_name):
    return is_fn(DIE) and is_fn_named(DIE, fn_name)


@lru_cache(maxsize=None)
def find_type_info(dwarf_info, value):
    for CU in dwarf_info.iter_CUs():
        for DIE in CU.iter_DIEs():
            if value == DIE.offset:
                return DIE


def get_type_string(dwarf_info, type_info):
    if is_ptr(type_info):
        pointed_to_type = find_type_info(dwarf_info, get_type_value(type_info))
        if pointed_to_type is None:
            return 'void*'
        return get_type_string(dwarf_info, pointed_to_type) + '*'
    elif is_array(type_info):
        num_elements = get_array_count(type_info)
        pointed_to_type = find_type_info(dwarf_info, get_type_value(type_info))
        return get_type_string(dwarf_info, pointed_to_type) + '[' + str(num_elements) + ']'
    elif is_const(type_info):
        pointed_to_type = find_type_info(dwarf_info, get_type_value(type_info))
        if pointed_to_type is None:
            print('WARNING: broken DIE: ', type_info)
            return ''
        return 'const ' + get_type_string(dwarf_info, pointed_to_type)
    elif is_struct(type_info):
        return 'struct ' + get_name(type_info)
    elif is_union(type_info):
        return 'union ' + get_name(type_info)
    elif is_enum(type_info):
        return 'enum ' + get_name(type_info)
    elif is_base_type(type_info) or is_typedef(type_info):
        return get_name(type_info)
    else:
        print('Unsupported type info for %s, implement me!' % (type_info.tag),
              file=sys.stderr)
        print(type_info, file=sys.stderr)


# Check out
# https://github.com/eliben/pyelftools/blob/097257942a8eb4fa76b37df4abdf4d2298bb9726/scripts/dwarfdump.py#L181
def get_location(dwarf_info, DIE):
    if 'DW_AT_location' in DIE.attributes:
        location = DIE.attributes['DW_AT_location']
        location_parser = LocationParser(dwarf_info.location_lists())
        loclist = location_parser.parse_from_attribute(
            location, DIE.cu.header.version, DIE)
        if isinstance(loclist, LocationExpr):
            exprparser = DWARFExprParser(DIE.cu.structs)
            parsed = exprparser.parse_expr(loclist.loc_expr)
            for dwarf_expr_op in parsed:
                reg = describe_reg_name(
                    dwarf_expr_op.op - 0x70, DIE.cu.dwarfinfo.config.machine_arch, True).upper()
                offset = str(dwarf_expr_op.args[0])
                # TODO: this assume only one location. What if there's more
                # than one, such as if a variable were spilled to different
                # locations?
                return reg + '+' + offset
    return ''


def print_var(dwarf_info, DIE):
    # print(DIE)
    if is_abstract(DIE):
        type_value = DIE.attributes['DW_AT_abstract_origin'].value
        ti = find_type_info(dwarf_info, type_value)
        print_var(dwarf_info, ti)
        return
    type_value = get_type_value(DIE)
    type_info = find_type_info(dwarf_info, type_value)
    type_string = get_type_string(dwarf_info, type_info)

    print('\t%d\t%-30s\t%-30s\t%s' %
          (get_byte_size(dwarf_info, type_info), type_string, get_name(DIE),
           get_location(dwarf_info, DIE)))


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
    if len(sys.argv) != 3:
        print('Usage: frame_larger_than.py <file> <function>')
        sys.exit(1)
    with open(sys.argv[1], 'rb') as f:
        try:
            elffile = ELFFile(f)
            if not elffile.has_dwarf_info():
                print('No dwarf info found in %s' % sys.argv[1])
                sys.exit(1)
            parse_file(elffile.get_dwarf_info(), sys.argv[2])
        except ELFError as e:
            print('failed to parse elf: %s' % e)
            sys.exit(1)
