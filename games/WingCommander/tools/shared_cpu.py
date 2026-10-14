"""Compile-time ISA selection for owned timing/prediction assembly, not game code.

020+ source is returned verbatim. 000 expansions preserve effective-address and
call flags/registers; math has the narrower explicit contracts in shared_math.s.
No native ABI, field offset, device or converter selection is implied.
"""
import re

UNITS = ('timing', 'timing_clock', 'timing_player', 'timing_input',
         'timing_presentation', 'timing_scene', 'timing_intro',
         'timing_translation', 'timing_projectiles', 'timing_scene_slots',
         'view_regions', 'release_buffer', 'frame_stats')
INDEX = re.compile(r'(?P<disp>\$[0-9a-f]+|-?\d+)?\((?P<base>a[0-6]),(?P<index>d[0-7])\.(?P<size>[wl])(?:\*(?P<scale>[1248]))?\)', re.I)
FAR = re.compile(r'(?P<disp>WC_NATIVE_[A-Z_]+|\$[0-9a-f]+|\d+)\((?P<base>a[0-6])\)', re.I)


def number(text):
    return int(text[1:], 16) if text.startswith('$') else int(text)


def select(source, cpu):
    if cpu in ('68020', '68030', '68040', '68060'):
        return source
    if cpu != '68000':
        raise ValueError('unsupported shared ISA: ' + cpu)
    result = []
    serial = 0
    for raw in source.splitlines():
        code, _, _comment = raw.partition(';')
        match = re.match(r'^(\s+)(\S+)\s+(.*?)\s*$', code)
        if not match:
            result.append(raw)
            continue
        _, op, args = match.groups()
        op = op.lower()
        serial += 1
        # Local labels keep the surrounding native .label scope intact.
        tag = f'.wc_cpu_{serial}'
        if op == 'move.w' and args.replace(' ', '') == 'ccr,-(sp)':
            result.append('        WC_PUSH_CCR')
        elif op in ('muls.l', 'mulu.l', 'divs.l'):
            # Audited callers consume values, not MUL/DIV condition codes.
            # Their subsequent ADD/CMP defines every live arithmetic flag.
            factor, dest = [x.strip() for x in args.split(',')]
            if dest not in ('d0', 'd1', 'd2', 'd3', 'd6') or factor not in ('d6', 'd7', '#10') or factor == dest:
                raise ValueError('unreviewed long arithmetic: ' + raw)
            macro = 'WC_DIV_RATE' if op == 'divs.l' else 'WC_MUL_SMALL'
            if macro == 'WC_DIV_RATE' and factor != 'd7':
                raise ValueError('division requires positive rate in D7')
            result.append(f'        {macro} {factor},{dest}')
        elif op in ('tst.b', 'tst.w', 'tst.l', 'cmpi.b', 'cmpi.w', 'cmpi.l') and '(pc)' in args:
            target = args.split(',')[-1].strip()
            if not target.endswith('(pc)'): raise ValueError('unreviewed PC operand')
            result += ['        movem.l a0,-(sp)', f'        lea {target},a0',
                       f'        {op} '+args.replace(target,'(a0)'), '        movem.l (sp)+,a0']
        elif op == 'bra.l':
            # Fail assembly if the selected linked unit exceeds word reach.
            result.append('        bra.w ' + args)
        elif INDEX.search(args) or any((m['disp'].startswith('WC_NATIVE_') or number(m['disp']) > 32767) for m in FAR.finditer(args)):
            if re.search(r'\bsp\b', args):
                raise ValueError('stack-relative expanded operand requires an explicit adapter')
            matches = list(INDEX.finditer(args))
            matches += [m for m in FAR.finditer(args) if (m['disp'].startswith('WC_NATIVE_') or number(m['disp']) > 32767)]
            matches.sort(key=lambda m: m.start())
            if op in ('jsr', 'jmp'):
                if len(matches) != 1 or matches[0].group() != args or INDEX.search(args):
                    raise ValueError('unreviewed indirect call: ' + raw)
                m = matches[0]
                # Synthetic return + tail dispatch leave the callee's argument
                # stack exactly where JSR puts it. No live register/CCR changes.
                if op == 'jsr': result.append(f'        pea {tag}(pc)')
                result += ['        lea -12(sp),sp', '        WC_PUSH_CCR', '        move.w (sp),2(sp)', '        lea 2(sp),sp',
                           '        move.l a0,2(sp)', f'        movea.l {m["base"]},a0',
                           f'        adda.l #{m["disp"]},a0', '        move.l a0,8(sp)',
                           '        movea.l 2(sp),a0', '        move.w (sp),ccr',
                           '        lea 8(sp),sp', '        rts']
                if op == 'jsr': result.append(tag + ':')
                continue
            if op not in ('move.b','move.w','move.l','cmp.b','cmp.w','cmp.l',
                          'cmpi.w','tst.b','tst.w','tst.l','clr.b','clr.w','clr.l','sub.w','lea'):
                raise ValueError('unreviewed expanded instruction: ' + raw)
            used = set(re.findall(r'\ba[0-6]\b', args))
            scratch = [f'a{i}' for i in range(7) if f'a{i}' not in used][:len(matches)]
            if len(scratch) != len(matches): raise ValueError('no address scratch')
            regs = '/'.join(scratch)
            result.append(f'        movem.l {regs},-(sp)')
            patched, last = '', 0
            for m, reg in zip(matches, scratch):
                result.append(f'        movea.l {m["base"]},{reg}')
                if m.re is INDEX:
                    for _ in range(int(m['scale'] or '1')):
                        result.append(f'        adda.{m["size"]} {m["index"]},{reg}')
                if m['disp']: result.append(f'        adda.l #{m["disp"]},{reg}')
                patched += args[last:m.start()] + f'({reg})'
                last = m.end()
            patched += args[last:]
            result += [f'        {op} {patched}', f'        movem.l (sp)+,{regs}']
        else:
            # Expansion changes distances. Word branches fail rather than emit
            # unsupported long branches; final link must still check PC reach.
            result.append(re.sub(r'\b(b(?:ra|sr|eq|ne|hi|ls|cc|cs|hs|lo|ge|lt|gt|le|pl|mi|vc|vs))\.s\b', r'\1.w', raw))
    return '\n'.join(result) + '\n'


def unit(root, name, cpu):
    if name not in UNITS: raise ValueError('not an audited shared source unit')
    return select((root / 'whdload' / (name + '.s')).read_text(), cpu)


def preamble(root, cpu):
    return (root / 'whdload/shared_math.s').read_text() if cpu == '68000' else ''
