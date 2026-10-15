; B8 full drawing adapter for SPS 0481, explicitly default-off.
; Native race ranges $654ec..$65542, $65606..$65714 and $6571a..$65d6e
; retain their instruction order and local branch targets. The host binds their
; absolute operands to live public hunks. B8 labels identify original addresses.
; Changes: complete original screen-pointer repair, simulation-owned wheel rates
; and view flag, presentation-only pit messages, split clocks/flags, and saved
; native buffer-pointer views. The blitter waits and native drawing remain.
; Caller has prepared B8RenderArena and owns the main-task render opportunity.
; No hook is installed by including this module.
 IFD FF1_RENDER_POSES
B8Draw:
 link a6,#-64
 move.l $226ae,-60(a6)
 move.l $226b2,-56(a6)
 lea -24(sp),sp
B8_654ec:
 move.w $66f88.l,d0
B8_654f2:
 ext.l d0
B8_654f4:
 move.l d0,-(a7)
B8_654f6:
 jsr $2428a.l
B8_654fc:
 addq.l #$4,a7
B8_654fe:
 move.w $66f88.l,d0
B8_65504:
 move.w $66fa4.l,d1
B8_6550a:
 eor.w d1,d0
B8_6550c:
 move.w d0,$66f88.l
B8_65512:
 ext.l d0
B8_65514:
 move.l d0,$14(a7)
B8_65518:
 lsl.l #4,d0
 move.l d0,a0
 ext.l d1
 move.w d1,$dff180
B8_6551e:
 adda.l #$66c92,a0
B8_65524:
 move.l a0,$226ae.l
B8_6552a:
 move.l $14(a7),d0
B8_6552e:
 eor.l d1,d0
B8_65530:
 asl.l #$2,d0
B8_65532:
 asl.l #$2,d0
B8_65534:
 movea.l d0,a0
B8_65536:
 adda.l #$66c92,a0
B8_6553c:
 move.l a0,$226b2.l
B8_65542:
B8_65606:
 move.w $1c6a2.l,d0
B8_6560c:
 asr.w #$2,d0
B8_6560e:
 move.w d0,$66f96.l
B8_65614:
 move.w $6a67a.l,d1
B8_6561a:
 ext.l d1
B8_6561c:
 ext.l d0
B8_6561e:
 add.l d0,d1
B8_65620:
 move.w $6a61a.l,d0
B8_65626:
 ext.l d0
B8_65628:
 move.l d0,-(a7)
B8_6562a:
 move.l d1,-(a7)
B8_6562c:
 jsr $25000.l
B8_65632:
 addq.l #$8,a7
B8_65634:
 move.w $6a67a.l,d1
B8_6563a:
 ext.l d1
B8_6563c:
 move.w $66f96.l,d2
B8_65642:
 ext.l d2
B8_65644:
 add.l d2,d1
B8_65646:
 move.w $6a62a.l,d2
B8_6564c:
 ext.l d2
B8_6564e:
 move.l d2,-(a7)
B8_65650:
 move.l d1,-(a7)
B8_65652:
 move.w d0,$14(a7)
B8_65656:
 jsr $24fe0.l
B8_6565c:
 addq.l #$8,a7
B8_6565e:
 move.w $c(a7),d1
B8_65662:
 sub.w d0,d1
B8_65664:
 move.w d1,$66f8a.l
B8_6566a:
 move.w $6a67a.l,d0
B8_65670:
 ext.l d0
B8_65672:
 move.w $66f96.l,d1
B8_65678:
 ext.l d1
B8_6567a:
 add.l d1,d0
B8_6567c:
 move.w $6a61a.l,d1
B8_65682:
 ext.l d1
B8_65684:
 move.l d1,-(a7)
B8_65686:
 move.l d0,-(a7)
B8_65688:
 jsr $24fe0.l
B8_6568e:
 addq.l #$8,a7
B8_65690:
 move.w $6a67a.l,d1
B8_65696:
 ext.l d1
B8_65698:
 move.w $66f96.l,d2
B8_6569e:
 ext.l d2
B8_656a0:
 add.l d2,d1
B8_656a2:
 move.w $6a62a.l,d2
B8_656a8:
 ext.l d2
B8_656aa:
 move.l d2,-(a7)
B8_656ac:
 move.l d1,-(a7)
B8_656ae:
 move.w d0,$14(a7)
B8_656b2:
 jsr $25000.l
B8_656b8:
 addq.l #$8,a7
B8_656ba:
 move.w $c(a7),d1
B8_656be:
 add.w d0,d1
B8_656c0:
 move.w d1,$66f8c.l
B8_656c6:
 move.w $6a66a.l,d0
B8_656cc:
 ext.l d0
B8_656ce:
 move.w $66f96.l,d1
B8_656d4:
 ext.l d1
B8_656d6:
 add.l d1,d0
B8_656d8:
 andi.l #$3ff,d0
B8_656de:
 move.l d0,-$34(a6)
B8_656e2:
 move.l d1,$10(a7)
B8_656e6:
 move.l #$7e0,d1
B8_656ec:
 jsr $29500.l
B8_656f2:
 moveq #$a,d1
B8_656f4:
 asr.l d1,d0
B8_656f6:
 move.l $10(a7),d1
B8_656fa:
 move.w d0,-$30(a6)
B8_656fe:
 move.l $32b6e.l,d0
B8_65704:
 jsr $29500.l
B8_6570a:
 moveq #$a,d1
B8_6570c:
 asr.l d1,d0
B8_6570e:
 move.w d0,$66faa.l
B8_65714:
B8_6571a:
 move.w #$1,$1c1b4.l
B8_65722:
 jsr $2a260.l
 IFD FF1_C4_ROAD_PREFETCH
 bsr.w FF1C4PrepareRoad
 ENDC
 IFD FF1_FINE_ROAD_PREFETCH
 bsr.w FF1RenderPrepareRoad
 ENDC
B8_65728:
 IFD FF1_FINE_ROAD_PREFETCH
 move.w FF1RenderRoadControl(pc),d0
 beq.b .fine_native_wait
 move.l schedule_context+FF1T_FIELDS(pc),d0
 cmp.l FF1RenderRoadField(pc),d0
 bne.w B8_65734
.fine_native_wait:
 ENDC
 IFD FF1_C4_ROAD_PREFETCH
 move.w C4RoadPrefetchEnabled(pc),d0
 beq.b .native_wait
 move.l C1Context(pc),d0
 cmp.l C4RoadField(pc),d0
 bne.w B8_65734
.native_wait:
 ENDC
 move.w $dff004.l,d0
B8_6572e:
 btst #$0,d0
B8_65732:
 beq.w B8_65728
B8_65734:
 jsr $6b050.l
B8_6573a:
 move.w -$30(a6),d0
B8_6573e:
 ext.l d0
B8_65740:
 move.l d0,-(a7)
B8_65742:
 jsr $6b950.l
B8_65748:
 addq.l #$4,a7
B8_6574a:
 move.w $6a67a.l,d0
B8_65750:
 move.w $66f96.l,d1
B8_65756:
 add.w d1,d0
B8_65758:
 andi.w #$3ff,d0
B8_6575c:
 move.w d0,-$2c(a6)
B8_65760:
 cmpi.w #$100,d0
B8_65764:
 ble.w B8_6577c
B8_65766:
 cmpi.w #$300,d0
B8_6576a:
 bge.w B8_6577c
B8_6576c:
 subi.w #$200,-$2c(a6)
B8_65772:
 nop
B8_6577a:
 bra.w B8_65782
B8_6577c:
 nop
B8_65782:
 move.w -$2c(a6),d0
B8_65786:
 ext.l d0
B8_65788:
 move.l d0,-(a7)
B8_6578a:
 IFD FF1_C4_ROAD_PREFETCH
 bsr.w FF1C4DrawPreparedRoad
 ELSE
 IFD FF1_FINE_ROAD_PREFETCH
 bsr.w FF1RenderDrawPreparedRoad
 ELSE
 jsr $6b368.l
 ENDC
 ENDC
B8_65790:
 addq.l #$4,a7
B8_65792:
 tst.w $66c7c.l
B8_65798:
 bne.w B8_657a6
B8_6579a:
 jsr $6bf90.l
B8_657a0:
 jsr $69bb8.l
B8_657a6:
 move.w $1c6a2.l,d0
B8_657ac:
 move.w d0,$c(a7)
B8_657b0:
 asr.w #$5,d0
B8_657b2:
 move.w d0,$10(a7)
B8_657b6:
 addi.w #$20,d0
B8_657ba:
 move.w $2275a.l,d1
B8_657c0:
 muls.w d1,d0
B8_657c2:
 asr.w #$4,d0
B8_657c4:
 nop
B8_657ca:
 move.w $10(a7),d0
B8_657ce:
 moveq #$20,d2
B8_657d0:
 sub.w d0,d2
B8_657d2:
 muls.w d2,d1
B8_657d4:
 asr.w #$4,d1
B8_657d6:
 nop
B8_657dc:
 move.w $c(a7),d0
B8_657e0:
 addi.w #$10,d0
B8_657e4:
 asr.w #$5,d0
B8_657e6:
 addq.w #$8,d0
B8_657e8:
 move.w d0,$66c86.l
B8_657ee:
 cmpi.w #$10,d0
B8_657f2:
 ble.w B8_657fc
B8_657f4:
 move.w #$10,$66c86.l
B8_657fc:
 move.w $66c86.l,d0
B8_65802:
 tst.w d0
B8_65804:
 bpl.w B8_6580c
B8_65806:
 clr.w $66c86.l
B8_6580c:
 move.w $66c86.l,d0
B8_65812:
 cmpi.w #$f,d0
B8_65816:
 bge.w B8_65a52
B8_6581a:
 move.w $6c942.l,d0
B8_65820:
 ext.l d0
B8_65822:
 asr.l #$2,d0
B8_65824:
 moveq #$1a,d1
B8_65826:
 move.l d1,-(a7)
B8_65828:
 move.l d0,-(a7)
B8_6582a:
 jsr $25000.l
B8_65830:
 addq.l #$8,a7
B8_65832:
 addi.w #$1c,d0
B8_65836:
 move.w d0,$66c82.l
B8_6583c:
 move.w $66c86.l,d1
B8_65842:
 ext.l d1
B8_65844:
 movea.l d1,a0
B8_65846:
 move.l a0,$c(a7)
B8_6584a:
 adda.l #$32c26,a0
B8_65850:
 ext.l d0
B8_65852:
 movea.l d0,a1
B8_65854:
 move.l a1,$14(a7)
B8_65858:
 adda.l #$32bd6,a1
B8_6585e:
 move.b (a0),d2
B8_65860:
 ext.w d2
B8_65862:
 ext.l d2
B8_65864:
 move.b (a1),d3
B8_65866:
 ext.w d3
B8_65868:
 ext.l d3
B8_6586a:
 move.l d2,d0
B8_6586c:
 move.l d3,d1
B8_6586e:
 jsr $29500.l
B8_65874:
 asr.l #$8,d0
B8_65876:
 move.w d0,$66c7e.l
B8_6587c:
 moveq #$e,d1
B8_6587e:
 move.l $66c5e.l,d2
B8_65884:
 lsr.l d1,d2
B8_65886:
 move.l d2,d0
B8_65888:
 jsr $29390.l
B8_6588e:
 move.w d0,-$2e(a6)
B8_65892:
 move.l $14(a7),d1
B8_65896:
 cmpi.l #$2b,d1
B8_6589c:
 bge.w B8_659b2
B8_658a0:
 ext.l d0
B8_658a2:
 cmpi.l #$a,d0
B8_658a8:
 blt.w B8_6592a
B8_658ac:
 subi.l #$9,d0
B8_658b2:
 asl.l #$2,d0
B8_658b4:
 movea.l d0,a0
B8_658b6:
 adda.l #$255f8,a0
B8_658bc:
 move.l $c(a7),d0
B8_658c0:
 asl.l #$5,d0
B8_658c2:
 movea.l d0,a1
B8_658c4:
 adda.l #$20dac,a1
B8_658ca:
 adda.w #$c,a1
B8_658ce:
 movea.l $c(a7),a2
B8_658d2:
 adda.l #$32c02,a2
B8_658d8:
 move.b (a2),d2
B8_658da:
 ext.w d2
B8_658dc:
 ext.l d2
B8_658de:
 move.w $66c7e.l,d3
B8_658e4:
 ext.l d3
B8_658e6:
 add.l d3,d2
B8_658e8:
 movea.l d0,a2
B8_658ea:
 adda.l #$20dac,a2
B8_658f0:
 move.w (a2),d0
B8_658f2:
 ext.l d0
B8_658f4:
 moveq #$1,d3
B8_658f6:
 move.l d3,-(a7)
B8_658f8:
 moveq #$3,d3
B8_658fa:
 move.l d3,-(a7)
B8_658fc:
 moveq #$2,d3
B8_658fe:
 move.l d3,-(a7)
B8_65900:
 moveq #$1,d3
B8_65902:
 move.l d3,-(a7)
B8_65904:
 moveq #$13,d3
B8_65906:
 move.l d3,-(a7)
B8_65908:
 move.l d0,-(a7)
B8_6590a:
 move.l d1,-(a7)
B8_6590c:
 move.l d2,-(a7)
B8_6590e:
 move.l a1,-(a7)
B8_65910:
 moveq #$2,d3
B8_65912:
 move.l d3,-(a7)
B8_65914:
 moveq #$0,d3
B8_65916:
 move.l d3,-(a7)
B8_65918:
 move.l d3,-(a7)
B8_6591a:
 move.l a0,-(a7)
B8_6591c:
 jsr $24ae0.l
B8_65922:
 lea $34(a7),a7
B8_65926:
 bra.w B8_659b2
B8_6592a:
 move.w -$2e(a6),d0
B8_6592e:
 ext.l d0
B8_65930:
 asl.l #$2,d0
B8_65932:
 movea.l d0,a0
B8_65934:
 adda.l #$255f8,a0
B8_6593a:
 move.w $66c86.l,d0
B8_65940:
 ext.l d0
B8_65942:
 move.l d0,$10(a7)
B8_65946:
 asl.l #$5,d0
B8_65948:
 movea.l d0,a1
B8_6594a:
 adda.l #$20dac,a1
B8_65950:
 adda.w #$c,a1
B8_65954:
 movea.l $10(a7),a2
B8_65958:
 adda.l #$32c02,a2
B8_6595e:
 move.b (a2),d1
B8_65960:
 ext.w d1
B8_65962:
 ext.l d1
B8_65964:
 move.w $66c7e.l,d2
B8_6596a:
 ext.l d2
B8_6596c:
 add.l d2,d1
B8_6596e:
 move.w $66c82.l,d2
B8_65974:
 ext.l d2
B8_65976:
 movea.l d0,a2
B8_65978:
 adda.l #$20dac,a2
B8_6597e:
 move.w (a2),d0
B8_65980:
 ext.l d0
B8_65982:
 moveq #$3,d3
B8_65984:
 move.l d3,-(a7)
B8_65986:
 moveq #$2,d3
B8_65988:
 move.l d3,-(a7)
B8_6598a:
 move.l d3,-(a7)
B8_6598c:
 moveq #$1,d3
B8_6598e:
 move.l d3,-(a7)
B8_65990:
 moveq #$13,d3
B8_65992:
 move.l d3,-(a7)
B8_65994:
 move.l d0,-(a7)
B8_65996:
 move.l d2,-(a7)
B8_65998:
 move.l d1,-(a7)
B8_6599a:
 move.l a1,-(a7)
B8_6599c:
 moveq #$2,d3
B8_6599e:
 move.l d3,-(a7)
B8_659a0:
 moveq #$0,d3
B8_659a2:
 move.l d3,-(a7)
B8_659a4:
 move.l d3,-(a7)
B8_659a6:
 move.l a0,-(a7)
B8_659a8:
 jsr $24ae0.l
B8_659ae:
 lea $34(a7),a7
B8_659b2:
 move.w $66c86.l,d0
B8_659b8:
 ext.l d0
B8_659ba:
 move.w $66faa.l,d1
B8_659c0:
 ext.l d1
B8_659c2:
 move.l d1,-(a7)
B8_659c4:
 move.l d0,-(a7)
B8_659c6:
 jsr $6ae70.l
B8_659cc:
 addq.l #$8,a7
B8_659ce:
 move.w $66c82.l,d0
B8_659d4:
 ext.l d0
B8_659d6:
 cmpi.l #$2b,d0
B8_659dc:
 bge.w B8_65a52
B8_659de:
 move.w $66c86.l,d1
B8_659e4:
 ext.l d1
B8_659e6:
 move.l d1,$10(a7)
B8_659ea:
 asl.l #$5,d1
B8_659ec:
 movea.l d1,a0
B8_659ee:
 adda.l #$20dac,a0
B8_659f4:
 adda.w #$c,a0
B8_659f8:
 movea.l $10(a7),a1
B8_659fc:
 adda.l #$32c02,a1
B8_65a02:
 move.b (a1),d2
B8_65a04:
 ext.w d2
B8_65a06:
 ext.l d2
B8_65a08:
 move.w $66c7e.l,d3
B8_65a0e:
 ext.l d3
B8_65a10:
 add.l d3,d2
B8_65a12:
 movea.l d1,a1
B8_65a14:
 adda.l #$20dac,a1
B8_65a1a:
 move.w (a1),d1
B8_65a1c:
 ext.l d1
B8_65a1e:
 moveq #$1,d3
B8_65a20:
 move.l d3,-(a7)
B8_65a22:
 move.l d3,-(a7)
B8_65a24:
 moveq #$2,d3
B8_65a26:
 move.l d3,-(a7)
B8_65a28:
 moveq #$1,d3
B8_65a2a:
 move.l d3,-(a7)
B8_65a2c:
 moveq #$13,d3
B8_65a2e:
 move.l d3,-(a7)
B8_65a30:
 move.l d1,-(a7)
B8_65a32:
 move.l d0,-(a7)
B8_65a34:
 move.l d2,-(a7)
B8_65a36:
 move.l a0,-(a7)
B8_65a38:
 moveq #$2,d3
B8_65a3a:
 move.l d3,-(a7)
B8_65a3c:
 moveq #$0,d3
B8_65a3e:
 move.l d3,-(a7)
B8_65a40:
 move.l d3,-(a7)
B8_65a42:
 pea.l $255f8.l
B8_65a48:
 jsr $24ae0.l
B8_65a4e:
 lea $34(a7),a7
B8_65a52:
 move.w $66c86.l,d0
B8_65a58:
 cmpi.w #$1,d0
B8_65a5c:
 ble.w B8_65c98
B8_65a60:
 move.w $6c944.l,d0
B8_65a66:
 ext.l d0
B8_65a68:
 asr.l #$2,d0
B8_65a6a:
 moveq #$1a,d1
B8_65a6c:
 move.l d1,-(a7)
B8_65a6e:
 move.l d0,-(a7)
B8_65a70:
 jsr $25000.l
B8_65a76:
 addq.l #$8,a7
B8_65a78:
 addi.w #$1c,d0
B8_65a7c:
 move.w d0,$66c84.l
B8_65a82:
 move.w $66c86.l,d1
B8_65a88:
 ext.l d1
B8_65a8a:
 movea.l d1,a0
B8_65a8c:
 move.l a0,$c(a7)
B8_65a90:
 adda.l #$32c38,a0
B8_65a96:
 ext.l d0
B8_65a98:
 movea.l d0,a1
B8_65a9a:
 move.l a1,$14(a7)
B8_65a9e:
 adda.l #$32bd6,a1
B8_65aa4:
 move.b (a0),d2
B8_65aa6:
 ext.w d2
B8_65aa8:
 ext.l d2
B8_65aaa:
 move.b (a1),d3
B8_65aac:
 ext.w d3
B8_65aae:
 ext.l d3
B8_65ab0:
 move.l d2,d0
B8_65ab2:
 move.l d3,d1
B8_65ab4:
 jsr $29500.l
B8_65aba:
 asr.l #$8,d0
B8_65abc:
 move.w d0,$66c80.l
B8_65ac2:
 moveq #$e,d1
B8_65ac4:
 move.l $66c5a.l,d2
B8_65aca:
 lsr.l d1,d2
B8_65acc:
 move.l d2,d0
B8_65ace:
 jsr $29390.l
B8_65ad4:
 move.w d0,-$2e(a6)
B8_65ad8:
 move.l $14(a7),d1
B8_65adc:
 cmpi.l #$2b,d1
B8_65ae2:
 bge.w B8_65bf8
B8_65ae6:
 ext.l d0
B8_65ae8:
 cmpi.l #$a,d0
B8_65aee:
 blt.w B8_65b70
B8_65af2:
 subi.l #$9,d0
B8_65af8:
 asl.l #$2,d0
B8_65afa:
 movea.l d0,a0
B8_65afc:
 adda.l #$255f8,a0
B8_65b02:
 move.l $c(a7),d0
B8_65b06:
 asl.l #$5,d0
B8_65b08:
 movea.l d0,a1
B8_65b0a:
 adda.l #$20fcc,a1
B8_65b10:
 adda.w #$c,a1
B8_65b14:
 movea.l $c(a7),a2
B8_65b18:
 adda.l #$32c14,a2
B8_65b1e:
 move.b (a2),d2
B8_65b20:
 ext.w d2
B8_65b22:
 ext.l d2
B8_65b24:
 move.w $66c80.l,d3
B8_65b2a:
 ext.l d3
B8_65b2c:
 add.l d3,d2
B8_65b2e:
 movea.l d0,a2
B8_65b30:
 adda.l #$20fcc,a2
B8_65b36:
 move.w (a2),d0
B8_65b38:
 ext.l d0
B8_65b3a:
 moveq #$1,d3
B8_65b3c:
 move.l d3,-(a7)
B8_65b3e:
 moveq #$3,d3
B8_65b40:
 move.l d3,-(a7)
B8_65b42:
 moveq #$2,d3
B8_65b44:
 move.l d3,-(a7)
B8_65b46:
 moveq #$1,d3
B8_65b48:
 move.l d3,-(a7)
B8_65b4a:
 moveq #$13,d3
B8_65b4c:
 move.l d3,-(a7)
B8_65b4e:
 move.l d0,-(a7)
B8_65b50:
 move.l d1,-(a7)
B8_65b52:
 move.l d2,-(a7)
B8_65b54:
 move.l a1,-(a7)
B8_65b56:
 moveq #$2,d3
B8_65b58:
 move.l d3,-(a7)
B8_65b5a:
 moveq #$0,d3
B8_65b5c:
 move.l d3,-(a7)
B8_65b5e:
 move.l d3,-(a7)
B8_65b60:
 move.l a0,-(a7)
B8_65b62:
 jsr $24ae0.l
B8_65b68:
 lea $34(a7),a7
B8_65b6c:
 bra.w B8_65bf8
B8_65b70:
 move.w -$2e(a6),d0
B8_65b74:
 ext.l d0
B8_65b76:
 asl.l #$2,d0
B8_65b78:
 movea.l d0,a0
B8_65b7a:
 adda.l #$255f8,a0
B8_65b80:
 move.w $66c86.l,d0
B8_65b86:
 ext.l d0
B8_65b88:
 move.l d0,$10(a7)
B8_65b8c:
 asl.l #$5,d0
B8_65b8e:
 movea.l d0,a1
B8_65b90:
 adda.l #$20fcc,a1
B8_65b96:
 adda.w #$c,a1
B8_65b9a:
 movea.l $10(a7),a2
B8_65b9e:
 adda.l #$32c14,a2
B8_65ba4:
 move.b (a2),d1
B8_65ba6:
 ext.w d1
B8_65ba8:
 ext.l d1
B8_65baa:
 move.w $66c80.l,d2
B8_65bb0:
 ext.l d2
B8_65bb2:
 add.l d2,d1
B8_65bb4:
 move.w $66c84.l,d2
B8_65bba:
 ext.l d2
B8_65bbc:
 movea.l d0,a2
B8_65bbe:
 adda.l #$20fcc,a2
B8_65bc4:
 move.w (a2),d0
B8_65bc6:
 ext.l d0
B8_65bc8:
 moveq #$3,d3
B8_65bca:
 move.l d3,-(a7)
B8_65bcc:
 moveq #$2,d3
B8_65bce:
 move.l d3,-(a7)
B8_65bd0:
 move.l d3,-(a7)
B8_65bd2:
 moveq #$1,d3
B8_65bd4:
 move.l d3,-(a7)
B8_65bd6:
 moveq #$13,d3
B8_65bd8:
 move.l d3,-(a7)
B8_65bda:
 move.l d0,-(a7)
B8_65bdc:
 move.l d2,-(a7)
B8_65bde:
 move.l d1,-(a7)
B8_65be0:
 move.l a1,-(a7)
B8_65be2:
 moveq #$2,d3
B8_65be4:
 move.l d3,-(a7)
B8_65be6:
 moveq #$0,d3
B8_65be8:
 move.l d3,-(a7)
B8_65bea:
 move.l d3,-(a7)
B8_65bec:
 move.l a0,-(a7)
B8_65bee:
 jsr $24ae0.l
B8_65bf4:
 lea $34(a7),a7
B8_65bf8:
 move.w $66c86.l,d0
B8_65bfe:
 ext.l d0
B8_65c00:
 move.w $66faa.l,d1
B8_65c06:
 ext.l d1
B8_65c08:
 move.l d1,-(a7)
B8_65c0a:
 move.l d0,-(a7)
B8_65c0c:
 jsr $6af7e.l
B8_65c12:
 addq.l #$8,a7
B8_65c14:
 move.w $66c84.l,d0
B8_65c1a:
 ext.l d0
B8_65c1c:
 cmpi.l #$2b,d0
B8_65c22:
 bge.w B8_65c98
B8_65c24:
 move.w $66c86.l,d1
B8_65c2a:
 ext.l d1
B8_65c2c:
 move.l d1,$10(a7)
B8_65c30:
 asl.l #$5,d1
B8_65c32:
 movea.l d1,a0
B8_65c34:
 adda.l #$20fcc,a0
B8_65c3a:
 adda.w #$c,a0
B8_65c3e:
 movea.l $10(a7),a1
B8_65c42:
 adda.l #$32c14,a1
B8_65c48:
 move.b (a1),d2
B8_65c4a:
 ext.w d2
B8_65c4c:
 ext.l d2
B8_65c4e:
 move.w $66c80.l,d3
B8_65c54:
 ext.l d3
B8_65c56:
 add.l d3,d2
B8_65c58:
 movea.l d1,a1
B8_65c5a:
 adda.l #$20fcc,a1
B8_65c60:
 move.w (a1),d1
B8_65c62:
 ext.l d1
B8_65c64:
 moveq #$1,d3
B8_65c66:
 move.l d3,-(a7)
B8_65c68:
 move.l d3,-(a7)
B8_65c6a:
 moveq #$2,d3
B8_65c6c:
 move.l d3,-(a7)
B8_65c6e:
 moveq #$1,d3
B8_65c70:
 move.l d3,-(a7)
B8_65c72:
 moveq #$13,d3
B8_65c74:
 move.l d3,-(a7)
B8_65c76:
 move.l d1,-(a7)
B8_65c78:
 move.l d0,-(a7)
B8_65c7a:
 move.l d2,-(a7)
B8_65c7c:
 move.l a0,-(a7)
B8_65c7e:
 moveq #$2,d3
B8_65c80:
 move.l d3,-(a7)
B8_65c82:
 moveq #$0,d3
B8_65c84:
 move.l d3,-(a7)
B8_65c86:
 move.l d3,-(a7)
B8_65c88:
 pea.l $255f8.l
B8_65c8e:
 jsr $24ae0.l
B8_65c94:
 lea $34(a7),a7
B8_65c98:
 IFD FF1_COARSE_STEP
 bsr.w B8PresentPit
 ELSE
 bsr.l B8PresentPit
 ENDC
B8_65c9e:
 move.w $6a66a.l,d0
B8_65ca4:
 andi.w #$3ff,d0
B8_65ca8:
 muls.w #$7e0,d0
B8_65cac:
 moveq #$a,d1
B8_65cae:
 asr.l d1,d0
B8_65cb0:
 move.l d0,-(a7)
B8_65cb2:
 jsr $6c0d0.l
B8_65cb8:
 addq.l #$4,a7
B8_65cba:
 move.w $66faa.l,d0
B8_65cc0:
 ext.l d0
B8_65cc2:
 move.l #$c0,d1
B8_65cc8:
 sub.l d0,d1
B8_65cca:
 move.w $1fdae.l,d0
B8_65cd0:
 ext.l d0
B8_65cd2:
 move.l #$c8,d2
B8_65cd8:
 sub.l d0,d2
B8_65cda:
 move.w $1fdb2.l,d0
B8_65ce0:
 ext.l d0
B8_65ce2:
 add.l d0,d2
B8_65ce4:
 move.l d2,-(a7)
B8_65ce6:
 move.l d1,-(a7)
B8_65ce8:
 pea.l $1fdac.l
B8_65cee:
 jsr $6ba18.l
B8_65cf4:
 lea $c(a7),a7
B8_65cf8:
 move.w $66faa.l,d0
B8_65cfe:
 ext.l d0
B8_65d00:
 move.l d0,-(a7)
B8_65d02:
 jsr $6bbfc.l
B8_65d08:
 addq.l #$4,a7
B8_65d0a:
 move.w $1c6a2.l,d0
B8_65d10:
 ext.l d0
B8_65d12:
 addq.l #$8,d0
B8_65d14:
 moveq #$20,d1
B8_65d16:
 jsr $293d0.l
B8_65d1c:
 addq.l #$8,d0
B8_65d1e:
 move.w $66faa.l,d1
B8_65d24:
 ext.l d1
B8_65d26:
 move.l d1,-(a7)
B8_65d28:
 move.l d0,-(a7)
B8_65d2a:
 jsr $6adf8.l
B8_65d30:
 addq.l #$8,a7
B8_65d32:
 tst.w $1bee8.l
B8_65d38:
 beq.w B8_65d6e
B8_65d3a:
 clr.w $23bb0.l
B8_65d40:
 move.w #$1,$23bb2.l
B8_65d48:
 moveq #$14,d0
B8_65d4a:
 move.l d0,-(a7)
B8_65d4c:
 moveq #$26,d0
B8_65d4e:
 move.l d0,-(a7)
B8_65d50:
 pea.l $32cd3.l
B8_65d56:
 IFD FF1_FINE_TEXT
 bsr.l FF1RenderDemoText
 ELSE
 jsr $239a0.l
 ENDC
B8_65d5c:
 lea $c(a7),a7
B8_65d60:
 move.w #$7,$23bb0.l
B8_65d68:
 clr.w $23bb2.l
B8_65d6e:
 IFD FF1_FINE_ROAD_PREFETCH
 bsr.w FF1RenderPresentHUD
 ELSE
 IFD FF1_COARSE_STEP
 bsr.w FF1PresentFlag
 ELSE
 bsr.l FF1PresentFlag
 ENDC
 IFD FF1_COARSE_STEP
 bsr.w FF1PresentClock
 ELSE
 bsr.l FF1PresentClock
 ENDC
 ENDC
 jsr $2a130
 jsr $2a270
 clr.w $1c1b4
 jsr $6694e
 jsr $2a130
 IFND FF1_PRODUCTION
 IFD FF1_COARSE_STEP
 lea B8Frames(pc),a0
 ELSE
 lea (B8Frames.l,pc),a0
 ENDC
 addq.l #1,(a0)
 ENDC
 move.l -60(a6),$226ae
 move.l -56(a6),$226b2
 unlk a6
 rts
B8Frames: dc.l 0
 IFD FF1_C4_ROAD_PREFETCH
 IFND FF1_COARSE_200_COMPLETE
 fail "Road prefetch requires complete C4"
 ENDC
 include "FerrariFormulaOne_Coarse200Road.s"
 ENDC
 ENDC
