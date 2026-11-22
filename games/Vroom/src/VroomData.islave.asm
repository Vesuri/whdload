
	; Vroom Data Disk imager

		incdir	Includes:
		include	RawDIC.i

		SLAVE_HEADER
		dc.b	1	; Slave version
		dc.b	0	; Slave flags
		dc.l	DSK_1	; Pointer to the first disk structure
		dc.l	Text	; Pointer to the text displayed in the imager window

		dc.b	"$VER: "
Text:		dc.b	"Vroom Data Disk imager V1.0",10,"by Mr.Larmer/Wanted Team on 02.02.2000",0
		cnop	0,4

DSK_1:		dc.l	0		; Pointer to next disk structure
		dc.w	1		; Disk structure version
		dc.w	0		; Disk flags
		dc.l	TL_1		; List of tracks which contain data
		dc.l	0		; UNUSED, ALWAYS SET TO 0!
		dc.l	FL_1		; List of files to be saved
		dc.l	0		; Table of certain tracks with CRC values
		dc.l	0		; Alternative disk structure, if CRC failed
		dc.l	0		; Called before a disk is read
		dc.l	0		; Called after a disk has been read

TL_1:
		TLENTRY 0,0,$1600,SYNC_STD,DMFM_STD
		TLENTRY 1,157,$16DC,SYNC_STD,DMFM_NR

		TLEND
FL_1:
		FLENTRY FL_NAME,0,FL_DISKLENGTH
		FLEND

FL_NAME		dc.b	'Disk.2',0
		even
DMFM_NR:
		move.w	d0,d7
		cmp.w	#$552A,(A0)
		bne.b	.error

		move.l	A1,A2

		move.l	#$55555555,D4
		moveq	#0,D0
		move.w	#$5B6,D3
.loop
		move.l	(A0)+,D1
		move.l	(A0)+,D2
		and.l	D4,D1
		and.l	D4,D2
		add.l	D1,D1
		or.l	D1,D2
		move.l	D2,(A1)+
		add.l	D2,D0
		dbra	D3,.loop

		tst.l	D0
		bne.s	.error
		cmpi.w	#$FE00,(A2)+
		bne.s	.error
		tst.b	(A2)+
		bne.s	.error
		cmp.b	(a2),d7
		bne.b	.error

		moveq	#IERR_OK,d0
		rts
.error
		moveq	#IERR_CHECKSUM,d0
		rts
