"""Compile-time variant selection. No fallback from OCS to CD32 definitions."""
from . import cd32, ocs


def get(name):
    try:
        return {'cd32': cd32, 'ocs': ocs}[name]
    except KeyError:
        raise ValueError('explicit variant must be cd32 or ocs') from None


def timing_hooks(variant, buffered=False):
    if not hasattr(variant, 'TIMING_HOOKS'):
        raise ValueError('enhanced timing is not implemented for ' + variant.NAME)
    hooks = list(variant.TIMING_HOOKS)
    if buffered:
        hooks = [(off, 'release_input_vblank' if label == 'timing_record_input' else label, op)
                 for off, label, op in hooks]
        hooks.extend(variant.BUFFERED_HOOKS)
    return hooks


def assembly_definitions(variant, symbols=False):
    """Equates only: selecting a map must emit no executable bytes or branches."""
    symbols = {}
    for prefix, values in (('NATIVE', variant.NATIVE), ('A4', variant.A4),
                           ('SCENE', variant.SCENE), ('OBJECTS', variant.OBJECTS),
                           ('BITMAP', {k: v for k, v in variant.BITMAP.items() if isinstance(v, int)})):
        symbols.update({f'WC_{prefix}_{key.upper()}': value for key, value in values.items()})
    if symbols:
        # Language symbols (german_map.py): the German build maps them.
        for key, value in variant.NATIVE.items():
            symbols[f'WC_NATIVE_{key.upper()}'] = f'E_{value:x}'
        for key, value in variant.A4.items():
            symbols[f'WC_A4_{key.upper()}'] = f'A_m{-value}' if value < 0 else f'A_{value}'
    return '\n'.join(f'{name} equ {value}' for name, value in symbols.items()) + '\n'
