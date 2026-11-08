# Boot beep stub, prepended to a DXE driver's entry point (x64, MS ABI: rcx=ImageHandle, rdx=SystemTable).
# ~1 kHz tone on the PC speaker (8254 counter 2 + NMI_SC port 0x61) for ~0.5 s, timed with the TSC
# (CPUID leaf 0x16 base MHz, fallback 2500 MHz). No calls, no memory writes besides the stack.
# Ends with 'jmp rel32' to the original entry point (displacement patched in by the build script).
    .intel_syntax noprefix
    .text
    .globl beep
beep:
    push    rbx
    push    rcx
    push    rdx
    mov     eax, 0x16
    xor     ecx, ecx
    cpuid                       # eax = processor base frequency in MHz
    and     eax, 0xFFFF
    cmp     eax, 400
    jb      1f
    cmp     eax, 8000
    jbe     2f
1:  mov     eax, 2500
2:  imul    rbx, rax, 500000    # cycles for 0.5 s
    mov     al, 0xB6            # counter 2, lobyte/hibyte, mode 3 (square wave), binary
    out     0x43, al
    mov     al, 0xA9            # divisor 0x04A9 = 1193 -> 1193182 / 1193 = ~1000 Hz
    out     0x42, al
    mov     al, 0x04
    out     0x42, al
    in      al, 0x61
    or      al, 0x03            # gate counter 2 + speaker data enable
    out     0x61, al
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    add     rbx, rax            # deadline
3:  pause
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    cmp     rax, rbx
    jb      3b
    in      al, 0x61
    and     al, 0xFC            # speaker off, counter 2 gate off
    out     0x61, al
    mov     al, 0xB0            # park counter 2: mode 0 (one-shot), so it no longer oscillates and
    out     0x43, al            # a later write that re-enables the speaker can't produce a tone
    mov     al, 0x01
    out     0x42, al
    xor     eax, eax
    out     0x42, al
    pop     rdx
    pop     rcx
    pop     rbx
    .byte   0xE9                # jmp rel32 -> original entry point
    .long   0
