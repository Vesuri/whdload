;*---------------------------------------------------------------------------
; Program:	unleashed.s
; Contents:	Stunt Car Racer Unleashed 1.1's enhanced framerate, as patches on the
;		original program running from its copy in ExpMem (CUSTOM3)
; Author:	Vesa Halttunen (Stunt Car Racer Unleashed: the disassembly, the
;		framerate work and every routine below)
; Info:		The routines are Unleashed 1.1's own, from its StuntCarRacer.s, with
;		its labels and comments; the glue around them and the patch table are
;		new. Unleashed is a reassembled game; here its changes go into the
;		original program instead: the patch table at the end writes each changed
;		instruction, or a jmp or jsr to the routine that replaces it, over the
;		program's copy. The symbols are the original program's addresses.
;
;		Built by tools/ulblob.py (docs/development.md), twice: with O=0 and with
;		every address in the program and in this blob moved by O=$100000. The
;		longwords that differ are the blob's relocations: the slave copies it
;		behind the program's copy and relocates both by the same distance, as if
;		it sat at $722e0 right after the program. What the blob reserves (its
;		variables and the fast render buffer) follows the code, in ExpMem.
;---------------------------------------------------------------------------*

		IFND	O
O		= 0
		ENDC
		IFND	NTSC
NTSC		= 0
		ENDC

	ifeq	NTSC
FRAMERATE_MULTIPLIER		equ	6				; 8FPS -> 48FPS PAL
	else
FRAMERATE_MULTIPLIER		equ	7				; 8FPS -> 56FPS NTSC
	endc
TIMESTEP_FACTOR			equ	$EE/FRAMERATE_MULTIPLIER	; originally $EE
MAJOR_IMPACT_COOLDOWN_TIME	equ	$FF				; originally $45

		INCLUDE	unleashed_syms.i

		ORG	$722e0+O

;======================================================================
; The header the slave reads after relocating the blob

ulHeader	dc.l	ulInstall		;jsr: clears what the blob reserves, writes the patches
		dc.l	ulRefreshBoost		;jsr: the F6 key (C1 at the start)
		dc.l	ulBssEnd-ulBss		;what the blob reserves behind its code
		dc.l	patchTable

;======================================================================
; The trainer key, from Unleashed's ciaAInterrupt

ulRefreshBoost:
	tst.b	boostFuelLevel
	bne.s	.toggleBoost
	move.b	maxBoostFuel,boostFuelLevel	;Lame trainer
.toggleBoost:
	eor.l	#1,infiniteBoost
		rts

;======================================================================

ulInstall	movem.l	d0-d1/a0-a1,-(sp)
		lea	ulBss,a0
		move.l	#(ulBssEnd-ulBss)/4-1,d0
.clear		clr.l	(a0)+
		dbf	d0,.clear
		lea	patchTable,a0
.next		move.l	(a0)+,d0		;site
		beq.b	.done
		movea.l	d0,a1
		move.w	(a0)+,d1		;bytes
		lsr.w	#1,d1
		subq.w	#1,d1
.copy		move.w	(a0)+,(a1)+
		dbf	d1,.copy
		bra.b	.next
.done		movem.l	(sp)+,d0-d1/a0-a1
		rts

;======================================================================
; The copper list: no copper interrupt at line $fa, the VBlank interrupt
; applies a pending frame buffer swap (copperInterrupt) instead.

verticalBlankInterrupt:
	bsr	copperInterrupt
	MOVEM.L	D0-D7/A0-A6,-(SP)
	CLR.W	D1
	CLR.W	D2
	JSR	verticalBlank
	BTST	#$05,_custom+serdatr
	BEQ	.done
	MOVE.B	serialWriteIndex,D0
	CMP.B	serialReadIndex,D0
	BEQ	.done
	JSR	serialTransmitEmptyInterrupt
.done:	MOVEM.L	(SP)+,D0-D7/A0-A6
	RTS

copperInterrupt:
	TST.B	copperlistUpdatePendingFlag
	BEQ	lbC000A46
	MOVEM.L	D0-D7/A0-A6,-(SP)
	JSR	updateCopperlistPointers
	CLR.B	copperlistUpdatePendingFlag
	move.b	framesSinceCopperlistUpdateAccumulator,framesSinceCopperlistUpdate
	clr.b	framesSinceCopperlistUpdateAccumulator
	TST.B	spriteUpdatePendingFlag
	BEQ	lbC000A42
	JSR	updateSpritePositions
	CLR.B	spriteUpdatePendingFlag
lbC000A42:
	MOVEM.L	(SP)+,D0-D7/A0-A6
lbC000A46:
	RTS


;======================================================================
; The fast render buffer: the 3D view is drawn into fast memory and copied
; into the chip frame buffer at the end of the frame (copyFastRenderBuffer).

setupFrameBufferAddresses:
	MOVE.L	#fastRenderBuffer,D3		; originally renderFrameBuffer
	ADD.L	#$00000284,D3
	MOVE.L	D3,viewportTopAddress
	MOVE.L	displayFrameBuffer,bitplane1Pointer
	MOVE.B	#$80,copperlistUpdatePendingFlag
.wait:	tst.b   copperlistUpdatePendingFlag	; added
	bmi	.wait
	RTS

copyMainGameBackground:
	MOVE.L	frameBuffers,A1
	MOVE.L	#imageMainGameBackground,A0
	JSR	decompressRLEImage
	MOVE.L	frameBuffers,A0
	MOVE.L	A0,A1
	ADD.W	#$7D00,A1
	lea	fastRenderBuffer,a2		; added
	MOVE.W	#$7D00/4-1,D3			; originally #$7CFF
.copyLoop:
	MOVE.L	(A0)+,D0			; originally MOVE.B	(A0)+,(A1)+
	move.l	d0,(A1)+
	move.l	d0,(A2)+
	DBRA	D3,.copyLoop
	RTS

; calculateCharacterScreenAddress, at the single buffer case
ulCharacterBuffer:
	tst.b	frameProcessingFlag		; added
	bmi.s	.fast
	MOVE.L	renderFrameBuffer,A1
		rts
.fast:	lea	fastRenderBuffer,a1
		rts

;======================================================================
; animateDrawBridge

ulDrawBridgeInactive:
	move.b	framesSinceCopperlistUpdate,d0			; added
	ADD.B	d0,drawBridgeAnimationPhase			; originally ADDQ.B #$01
	cmp.b	#$c0,drawBridgeAnimationPhase			; added
	bcs.s	.animationPhaseOk
	clr.b	drawBridgeAnimationPhase
.animationPhaseOk:
	MOVE.W	#$0000,segmentProgressDistance
	MOVE.B	#$00,drawBridgeActive
	MOVE.B	drawBridgeAnimationPhase,D0
	AND.W	#$00FF,D0					; originally $1F
	SUB.W	#$0010*FRAMERATE_MULTIPLIER,D0			; originally $10
	BPL	.animationPhasePositive
	NOT.W	D0
.animationPhasePositive:
	MOVE.B	D0,D2
;	ADDQ.W	#$04,D0
;	MOVE.L	#drawBridgeAngleTable,A0			; dead code
;	MOVE.B	$00(A0,D2.W),lbB00E285
;	MOVE.B	$00(A0,D2.W),lbB00E286
;	ASL.W	#$05,D0
	MOVE.W	D0,tempWord1
	add.w	d0,d0						; added
	add.w	d0,d0
	add.w	#128,d0
	add.w	d0,tempWord1
		jmp	O+$5a854

;======================================================================
; handleRaceStartCountdown

ulDecrementTimer:
	tst.b	frameThrottleFlag			; added
	bmi.s	.timerOk
	SUBQ.B	#$01,raceStartTimer
.timerOk:
		rts

;======================================================================
; The main loop: as many physics steps as fields went by

ulPhysicsLoop:
	move.b	framesSinceCopperlistUpdate,framesToProcess		; added
	sub.b	#1,framesToProcess
.loop:	JSR	processPlayerInput
	JSR	updateGamePhysics
	JSR	updateEngineAudioPitch
	JSR	processGameFrame
	sub.b	#1,framesToProcess
	bpl	.loop
		rts

ulRaceOver:	clr.b	frameProcessingFlag		; added
		tst.b	raceCompletionState
		rts

ulRestartCountdown:
	move.b	framesSinceCopperlistUpdate,d0
	SUB.B	d0,restartTimerCountdown		; originally #$01
		rts

ulRestartCountdownAdd:
	ADD.B	d0,restartTimerCountdown		; originally #$01
		rts

;======================================================================
; handlePause: the pause message straight to chip memory

ulPauseMessage:
	clr.b	frameProcessingFlag		; added
	MOVE.L	displayFrameBuffer,renderFrameBuffer
		rts

ulPauseMessageDone:
		jsr	updateGameMessageDisplay
	move.b	#$80,frameProcessingFlag	; added
		rts

;======================================================================
; updateFrameThrottlingAndTimers

ulLapTimeDisplay:
	move.b	framesSinceCopperlistUpdate,d1			; added
	cmp.b	d1,d0
	bls.s	.handleLapCompletion
	sub.b	d1,lapTimeDisplayDuration
	bra.s	.lapCompletionHandled
.handleLapCompletion:
	clr.b	lapTimeDisplayDuration
		jsr	handleLapCompletionTiming
.lapCompletionHandled:
		jmp	O+$5db72

;======================================================================

ulUpdateLapTimer:
	tst.b	frameThrottleFlag	; added
	bne	ulLapTimerDone		; lbC04F8AC: the original's, out of a branch's range
	MOVE.B	#$14,D0			; originally #$13
	moveq	#0,d3			; added
	move.b	framesSinceCopperlistUpdate,d3
	subq	#2,d3
	bmi.s	.incrementLapTimeBCD
	move.b	d0,d2
.loop:	abcd	d2,d0
	dbra	d3,.loop
.incrementLapTimeBCD:
		jmp	incrementLapTimeBCD	; the original's, out of a branch's range
ulLapTimerDone	jmp	lbC04F8AC

;======================================================================

updateDamageAndTimers:
	MOVE.B	damageAccumulationActive,D0
	BEQ	.damageBarUpdated
	MOVE.B	accumulatedForceFrontLeft,D0
	ADD.B	accumulatedForceFrontRight,D0
	ROXR.B	#$01,D0
	ADD.B	accumulatedForceRear,D0
	ROXR.B	#$01,D0
	MOVE.B	D0,targetDamageLevel
	JSR	updateDamageBarHUD
.damageBarUpdated:
	MOVE.B	majorImpactCooldownTimer,D0
	BEQ	.checkDamageAccumulation
;	SUBQ.B	#$01,majorImpactCooldownTimer	; originally
	move.b	framesSinceCopperlistUpdate,d2	; added
	cmp.b	d2,d0
	bcc.s	.deltaOk
	move.b	d0,d2
.deltaOk:
	sub.b	d2,majorImpactCooldownTimer
	CMP.B	#MAJOR_IMPACT_COOLDOWN_TIME,D0
	BEQ	.majorImpact
	MOVE.B	damageAccumulationActive,D0
	BNE	.minorImpact
	RTS

.majorImpact:
	MOVE.B	holeRenderingPosition,D2
	JSR	renderExistingHole
	BRA	.minorImpact			; originally JMP

.checkDamageAccumulation:
	MOVE.B	damageAccumulationActive,D0
	BEQ	.done
	MOVE.W	maxCompressionVelocity,D0
	CMP.W	#$1400,D0
	BCS	.minorImpact
	MOVE.B	holeRenderingPosition,D2
	BEQ	.minorImpact
	SUBQ.B	#$01,D2
	MOVE.B	D2,holeRenderingPosition
	JSR	renderNewHole
	MOVE.B	#MAJOR_IMPACT_COOLDOWN_TIME,D0
	MOVE.B	D0,majorImpactCooldownTimer
;	MOVE.B	#$0A,D0					; removed: unnecessary code
	MOVE.B	#$05,D0					; major impact
	BRA	.playSample				; originally BNE
.minorImpact:
	tst.b	creakingSoundCooldownTimer		; added
	bne.s	.sampleOk
	MOVE.B	maxCompressionVelocity,D0
	CMP.B	#$07,D0
	BCC	.velocityOk
	MOVE.B	#$07,D0
.velocityOk:
	ASL.B	#$02,D0
	CMP.B	#$40,D0
	BCS	.volumeOk
	MOVE.B	#$40,D0
.volumeOk:
	MOVE.B	D0,audioSample4Volume
	MOVE.B	#$04,D0					; creaking
	ifeq	NTSC					; added
	move.b	#17,creakingSoundCooldownTimer
	else
	move.b	#20,creakingSoundCooldownTimer
	endc
.playSample:
	JSR	playSample
.sampleOk:
	MOVE.B	#$00,D0
	MOVE.B	D0,damageAccumulationActive
.done:	RTS

;======================================================================

ulUpdateBoostFuelDisplay:
	tst.l	infiniteBoost			; added
	bne.s	.boostOk
	MOVE.B	boostFuelLevel,D3
	ANDI.B	#$0F,CCR
	ABCD	D3,D0
	CMP.B	maxBoostFuel,D0
	BCS	.maxOk
	MOVE.B	maxBoostFuel,D0
.maxOk:	MOVE.B	D0,boostFuelLevel
.boostOk:
		jmp	O+$60846

;======================================================================


handleGroundCollision:
	MOVE.B	#$06,grindSampleID	; ground grind
	MOVE.B	carSpeedMagnitude,D0
	CMP.B	#$10,D0
	BLT	lbC0525AC
	MOVE.B	#$10,D0
lbC0525AC:
	MOVE.B	D0,collisionImpactLevel
	MOVE.B	#$0F,D1
	TST.B	networkGameMode
	BEQ	lbC0525C4
	MOVE.B	#$03,D1
lbC0525C4:
	JSR	generateRandomNumber
	AND.W	#$001C,D0
	ADD.W	#$01C2,D0
	MOVE.W	D0,sampleGroundCollisionPeriod
	BRA	setParticleCountAndPlayGrindSound

noEdgeCollision:
	tst.b	offTrackStateFlags	; added
	bmi.s	.cooldownOk
	clr.b	grindSoundCooldownTimer
.cooldownOk:
	RTS


handleEdgeCollision:
	MOVE.B	#$01,grindSampleID		; egde grind
	MOVE.B	wheelBouncePhaseAccumulator,D0
	BNE	lbC052614
	MOVE.B	postWreckStateFlag,D0
	BEQ	noEdgeCollision
lbC052614:
	TST.B	offTrackStateFlags
	BMI	noEdgeCollision
	MOVE.B	carSpeedMagnitude,D0
	CMP.B	#$01,D0
	BLT	noEdgeCollision
	CMP.B	#$32,D0
	BLT	lbC052638
	MOVE.B	#$32,D0
lbC052638:
	MOVE.B	D0,collisionImpactLevel
	MOVE.B	#$1F,D1
	JSR	generateRandomNumber
	AND.B	#$07,D0
	MOVE.B	D0,D2
	MOVE.B	collisionImpactLevel,D0
	LSR.B	#$01,D0
;	BRA	lbC052682

;	CMP.B	#$08,D0			; removed: dead code
;	BGE	lbC05266A
;	MOVE.B	#$08,D0
;	BNE	lbC052682
;lbC05266A:
;	CMP.B	#$06,D2
;	BLT	lbC052682
;	MOVE.B	#$0D,D0
;	CMP.B	#$07,D2
;	BNE	lbC052682
;	MOVE.B	#$03,D0
;lbC052682:
	CMP.B	#$1F,D0
	BCS	lbC05268E
	MOVE.B	#$1F,D0
lbC05268E:
	EOR.B	#$1F,D0
	AND.W	#$00FF,D0
	ASL.W	#$02,D0
	ADD.W	#$00AA,D0
	MOVE.W	D0,sampleGrindPeriod
setParticleCountAndPlayGrindSound:
	ASL.B	#$01,D1
	MOVE.B	D1,opponentTargetLateralPosition
	MOVE.B	wheelMovementActive,D0
	BNE	.initializeOk		; the original's, out of a branch's range
	JMP	initializeDebrisParticlePositions
.initializeOk:
	tst.b	grindSoundCooldownTimer		; added
	bne.s	.soundDone
	MOVE.B	grindSampleID,D0
	JSR	playSample
.soundDone:
	add.b	#1,grindSoundCooldownTimer
	cmp.b	#FRAMERATE_MULTIPLIER,grindSoundCooldownTimer
	ble.s	.cooldownDone
	clr.b	grindSoundCooldownTimer
.cooldownDone:
	MOVE.L	#debrisParticleXPositions,A4
	MOVE.L	#debrisParticleXVelocities,A5
	MOVE.B	opponentTargetLateralPosition,D1
.updateParticlesLoop:
	JSR	validateAndRenderParticle
	BNE	.particleUpdated
	ADDQ.W	#$01,$40(A5,D1.W)	; originally #$02
	MOVE.W	$40(A5,D1.W),D0
	ADD.W	D0,$40(A4,D1.W)
	MOVE.W	$00(A5,D1.W),D0
	ADD.W	D0,$00(A4,D1.W)
.particleUpdated:
	SUBQ.B	#$02,D1
	BPL	.updateParticlesLoop
	MOVE.B	opponentTargetLateralPosition,D1
.respawnOffscreenParticlesLoop:
	MOVE.W	$40(A4,D1.W),D0
	CMP.W	#$0080,D0
	BCS	.particleOk
	JSR	generateRandomNumber
	AND.W	#$0007,D0
	MOVE.W	D0,D3
	CLR.W	D0
	MOVE.B	collisionImpactLevel,D0
	LSR.W	#$02,D0			; originally #$01
	TST.B	offTrackStateFlags
	BMI	.yVelocityOk
	LSR.W	#$01,D0
.yVelocityOk:
	ADD.W	D3,D0
	NOT.W	D0
	MOVE.W	D0,$40(A5,D1.W)
	TST.B	offTrackStateFlags
	BPL	.edgeCollision
	JSR	initializeDustCloudParticle
	JMP	.coordinatesOk

.edgeCollision:
	JSR	generateRandomNumber
	AND.W	#$007F,D0
	ADD.W	#$0040,D0
	MOVE.W	D0,$00(A4,D1.W)
	MOVE.W	D0,D5
	JSR	generateRandomNumber
	OR.W	#$FFF8,D0
	ADD.W	#$007F,D0
	MOVE.W	D0,$40(A4,D1.W)
.coordinatesOk:
	MOVE.W	D5,D0
	SUB.W	#$0080,D0
	ASR.W	#$04,D0			; originally #$03
	MOVE.W	D0,$00(A5,D1.W)
	JSR	validateAndRenderParticle
.particleOk:
	SUBQ.B	#$02,D1
	BPL	.respawnOffscreenParticlesLoop
	RTS

renderDustCloud:
	MOVE.B	D1,D2
	LSR.B	#$01,D2
	ADD.B	frameCounter,D2
	AND.W	#$000F,D2
	MOVE.L	#dustCloudAnimSequence,A0
	MOVE.B	$00(A0,D2.W),D2
	ASL.B	#$01,D2
	MOVE.W	$00(A4,D1.W),D4
	MOVE.L	#dustCloudOffsetTable,A0
	SUB.W	$00(A0,D2.W),D4
	ADD.W	#$0020,D4
	cmp.w	#$fe,d4			; added
	bcs.s	.xOk
	rts
.xOk:	MOVE.W	$40(A4,D1.W),D5
	ADD.W	#$0010,D5
	MOVE.B	D2,D0
	LSR.B	#$01,D0
	ADD.B	#$1D,D0
	JMP	renderGraphicsObjectAtPosition

ulCameraAngleY:
	muls	#TIMESTEP_FACTOR,d0	; added
	asr.l	#8,d0
	ADD.W	D0,cameraAngleY
		rts

;======================================================================

updateVelocityDamping:
	MOVE.W	rotationSpeedX,D3
	tst.b	wheelMovementActive	; added
	bne.s	.groundDampingX
	ASR.W	#$04,D3
	MOVE.W	targetPitchRate,D0
	SUB.W	D3,D0
;	TST.B	wheelMovementActive
	BRA.S	lbC053A5C		; originally BEQ
.groundDampingX:
	asr.w	#1,d3			; added
	MOVE.W	targetPitchRate,D0
	SUB.W	D3,D0
	MOVE.W	adjustedYawAngle,D3
	ASR.W	#$02,D3
	ADD.W	D3,D0
lbC053A5C:
	MOVE.W	D0,angularAccelerationX
	MOVE.W	rotationSpeedZ,D3
	tst.b	wheelMovementActive	; added
	bne.s	.groundDampingZ
	ASR.W	#$04,D3
	bra.s	.speedZOk
.groundDampingZ:
	asr.w	#1,d3			; added
.speedZOk:
	MOVE.W	targetRollRate,D0
	SUB.W	D3,D0
	MOVE.W	D0,angularAccelerationZ
	RTS

;======================================================================
; calculateOpponentCollisionForces

ulOpponentCollisionDamage:
	tst.b	frameThrottleFlag				 ; added
	bmi	.skipCollisionDamage
		MOVE.W	#$0200,D3
		MOVE.W	lateralOpponentCollisionForce,D0
		rts
.skipCollisionDamage:
		addq.l	#4,sp
		rts

;======================================================================

ulDisplayMenuScreen:
	clr.b	frameProcessingFlag		; added
	MOVE.W	imageMenuScreenPalette,D0
		rts

;======================================================================
; processGameFrame

ulSetupRendering:
	tst.b	framesToProcess				; added
	beq.s	.continueSetup
		addq.l	#4,sp			; out of processGameFrame, as Unleashed's rts
	rts
.continueSetup:
		MOVE.B	#$80,D0
		MOVE.B	D0,processedSegmentIndices1
		rts

ulGameFrameDone:
		JSR	updateGameMessageDisplay
	JSR	copyFastRenderBuffer
	RTS

copyFastRenderBuffer:
	lea	fastRenderBuffer,a0
	move.l	renderFrameBuffer,a1
	lea	16*40+4(a0),a0
	lea	16*40+4(a1),a1
	moveq	#4-1,d7
.copyBitplane:
	move.w	#128-1,d6
.copyMain:
	move.l	(a0)+,(a1)+
	move.l	(a0)+,(a1)+
	move.l	(a0)+,(a1)+
	move.l	(a0)+,(a1)+
	move.l	(a0)+,(a1)+
	move.l	(a0)+,(a1)+
	move.l	(a0)+,(a1)+
	move.l	(a0)+,(a1)+
	lea	8(a0),a0
	lea	8(a1),a1
	dbra	d6,.copyMain	
	moveq	#16-1,d6
.copyBottom:
	move.l	(a0),(a1)
	move.l	28(a0),28(a1)
	lea	40(a0),a0
	lea	40(a1),a1
	dbra	d6,.copyBottom
	lea	(200-128-16)*40(a0),a0
	lea	(200-128-16)*40(a1),a1
	dbra	d7,.copyBitplane
	rts

;======================================================================
; No self-modifying code: plotPixel and applyBitplaneMask jump into tables

setPixelColor:
;	LSR.B	#$01,D0
;	BCS	lbC057C62
;	BCLR	#$06,lbB057D05
;	BCLR	#$06,lbB057D1B
;	BRA	lbC057C72
;
;lbC057C62:
;	BSET	#$06,lbB057D05
;	BSET	#$06,lbB057D1B
;lbC057C72:
;	LSR.B	#$01,D0
;	BCS	lbC057C8C
;	BCLR	#$06,lbB057D09
;	BCLR	#$06,lbB057D1D
;	BRA	lbC057C9C
;
;lbC057C8C:
;	BSET	#$06,lbB057D09
;	BSET	#$06,lbB057D1D
;lbC057C9C:
;	LSR.B	#$01,D0
;	BCS	lbC057CB6
;	BCLR	#$06,lbB057D0D
;	BCLR	#$06,lbB057D21
;	BRA	lbC057CC6
;
;lbC057CB6:
;	BSET	#$06,lbB057D0D
;	BSET	#$06,lbB057D21
;lbC057CC6:
;	LSR.B	#$01,D0
;	BCS	lbC057CE0
;	BCLR	#$06,lbB057D11
;	BCLR	#$06,lbB057D25
;	BRA	lbC057CF0
;
;lbC057CE0:
;	BSET	#$06,lbB057D11
;	BSET	#$06,lbB057D25
;lbC057CF0:
	ext.w	d0
	lsl.w	#5,d0
	addq	#2,d0
	move.w	d0,plotPixelOffset
	RTS

plotPixel:
	MOVE.B	D4,D0
;	AND.W	#$000F,D0
;	EOR.W	#$000F,D0
;	CMP.W	#$0008,D0
;	BGE	.highByte
;	dc.b	$01					; BSET/BCLR $D0,$0001(A0)
;lbB057D05:
;	dc.b	$E8,$00,$01,$01				; BSET/BCLR D0,$1F41(A0)
;lbB057D09:
;	dc.b	$E8,$1F,$41,$01				; BSET/BCLR D0,$3E81(A0)
;lbB057D0D:
;	dc.b	$E8,$3E,$81,$01				; BSET/BCLR D0,$5DC1(A0)
;lbB057D11:
;	dc.b	$E8,$5D,$C1
	move.w	d1,-(sp)
	move.w	plotPixelOffset,d1
	not.b	d0
	btst	#3,d0
	bne	.highByte
	jmp	*+2(pc,d1.w)
	bclr	d0,$0001(a0)
	bclr	d0,$1f41(a0)
	bclr	d0,$3e81(a0)
	bclr	d0,$5dc1(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bset	d0,$0001(a0)
	bclr	d0,$1f41(a0)
	bclr	d0,$3e81(a0)
	bclr	d0,$5dc1(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bclr	d0,$0001(a0)
	bset	d0,$1f41(a0)
	bclr	d0,$3e81(a0)
	bclr	d0,$5dc1(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bset	d0,$0001(a0)
	bset	d0,$1f41(a0)
	bclr	d0,$3e81(a0)
	bclr	d0,$5dc1(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bclr	d0,$0001(a0)
	bclr	d0,$1f41(a0)
	bset	d0,$3e81(a0)
	bclr	d0,$5dc1(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bset	d0,$0001(a0)
	bclr	d0,$1f41(a0)
	bset	d0,$3e81(a0)
	bclr	d0,$5dc1(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bclr	d0,$0001(a0)
	bset	d0,$1f41(a0)
	bset	d0,$3e81(a0)
	bclr	d0,$5dc1(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bset	d0,$0001(a0)
	bset	d0,$1f41(a0)
	bset	d0,$3e81(a0)
	bclr	d0,$5dc1(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bclr	d0,$0001(a0)
	bclr	d0,$1f41(a0)
	bclr	d0,$3e81(a0)
	bset	d0,$5dc1(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bset	d0,$0001(a0)
	bclr	d0,$1f41(a0)
	bclr	d0,$3e81(a0)
	bset	d0,$5dc1(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bclr	d0,$0001(a0)
	bset	d0,$1f41(a0)
	bclr	d0,$3e81(a0)
	bset	d0,$5dc1(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bset	d0,$0001(a0)
	bset	d0,$1f41(a0)
	bclr	d0,$3e81(a0)
	bset	d0,$5dc1(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bclr	d0,$0001(a0)
	bclr	d0,$1f41(a0)
	bset	d0,$3e81(a0)
	bset	d0,$5dc1(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bset	d0,$0001(a0)
	bclr	d0,$1f41(a0)
	bset	d0,$3e81(a0)
	bset	d0,$5dc1(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bclr	d0,$0001(a0)
	bset	d0,$1f41(a0)
	bset	d0,$3e81(a0)
	bset	d0,$5dc1(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bset	d0,$0001(a0)
	bset	d0,$1f41(a0)
	bset	d0,$3e81(a0)
	bset	d0,$5dc1(a0)
	move.w	(sp)+,d1
	RTS

.highByte:
;	AND.W	#$0007,D0
;	dc.b	$01					; BSET/BCLR D0,(A0)
;lbB057D1B:
;	dc.b	$D0,$01					; BSET/BCLR D0,$1F40(A0)
;lbB057D1D:
;	dc.b	$E8,$1F,$40,$01				; BSET/BCLR D0,$3E80(A0)
;lbB057D21:
;	dc.b	$E8,$3E,$80,$01				; BSET/BCLR D0,$5DC0(A0)
;lbB057D25:
;	dc.b	$E8,$5D,$C0
	jmp	*+2(pc,d1.w)
	bclr	d0,$0000(a0)
	bclr	d0,$1f40(a0)
	bclr	d0,$3e80(a0)
	bclr	d0,$5dc0(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bset	d0,$0000(a0)
	bclr	d0,$1f40(a0)
	bclr	d0,$3e80(a0)
	bclr	d0,$5dc0(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bclr	d0,$0000(a0)
	bset	d0,$1f40(a0)
	bclr	d0,$3e80(a0)
	bclr	d0,$5dc0(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bset	d0,$0000(a0)
	bset	d0,$1f40(a0)
	bclr	d0,$3e80(a0)
	bclr	d0,$5dc0(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bclr	d0,$0000(a0)
	bclr	d0,$1f40(a0)
	bset	d0,$3e80(a0)
	bclr	d0,$5dc0(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bset	d0,$0000(a0)
	bclr	d0,$1f40(a0)
	bset	d0,$3e80(a0)
	bclr	d0,$5dc0(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bclr	d0,$0000(a0)
	bset	d0,$1f40(a0)
	bset	d0,$3e80(a0)
	bclr	d0,$5dc0(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bset	d0,$0000(a0)
	bset	d0,$1f40(a0)
	bset	d0,$3e80(a0)
	bclr	d0,$5dc0(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bclr	d0,$0000(a0)
	bclr	d0,$1f40(a0)
	bclr	d0,$3e80(a0)
	bset	d0,$5dc0(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bset	d0,$0000(a0)
	bclr	d0,$1f40(a0)
	bclr	d0,$3e80(a0)
	bset	d0,$5dc0(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bclr	d0,$0000(a0)
	bset	d0,$1f40(a0)
	bclr	d0,$3e80(a0)
	bset	d0,$5dc0(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bset	d0,$0000(a0)
	bset	d0,$1f40(a0)
	bclr	d0,$3e80(a0)
	bset	d0,$5dc0(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bclr	d0,$0000(a0)
	bclr	d0,$1f40(a0)
	bset	d0,$3e80(a0)
	bset	d0,$5dc0(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bset	d0,$0000(a0)
	bclr	d0,$1f40(a0)
	bset	d0,$3e80(a0)
	bset	d0,$5dc0(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bclr	d0,$0000(a0)
	bset	d0,$1f40(a0)
	bset	d0,$3e80(a0)
	bset	d0,$5dc0(a0)
	move.w	(sp)+,d1
	RTS
	nop
	nop
	nop
	nop
	nop
	nop
	bset	d0,$0000(a0)
	bset	d0,$1f40(a0)
	bset	d0,$3e80(a0)
	bset	d0,$5dc0(a0)
	move.w	(sp)+,d1
	RTS


applyBitplaneMask:
	MOVE.W	D4,D2
	NOT.W	D2
	moveq	#0,d0
	move.b	lbB057D75,d0
	jmp	*+2(pc,d0.w)
;	dc.w	$6000					; original BRA.W + self modifying code
;	ds.b	1
;lbB057D75:
;	dc.b	$02

lbC057D76:
	AND.W	D2,(A4)+
	AND.W	D2,$1F3E(A4)
	AND.W	D2,$3E7E(A4)
	AND.W	D2,$5DBE(A4)
	RTS

	OR.W	D4,(A4)+
	AND.W	D2,$1F3E(A4)
	AND.W	D2,$3E7E(A4)
	AND.W	D2,$5DBE(A4)
	RTS

	AND.W	D2,(A4)+
	OR.W	D4,$1F3E(A4)
	AND.W	D2,$3E7E(A4)
	AND.W	D2,$5DBE(A4)
	RTS

	OR.W	D4,(A4)+
	OR.W	D4,$1F3E(A4)
	AND.W	D2,$3E7E(A4)
	AND.W	D2,$5DBE(A4)
	RTS

	AND.W	D2,(A4)+
	AND.W	D2,$1F3E(A4)
	OR.W	D4,$3E7E(A4)
	AND.W	D2,$5DBE(A4)
	RTS

	OR.W	D4,(A4)+
	AND.W	D2,$1F3E(A4)
	OR.W	D4,$3E7E(A4)
	AND.W	D2,$5DBE(A4)
	RTS

	AND.W	D2,(A4)+
	OR.W	D4,$1F3E(A4)
	OR.W	D4,$3E7E(A4)
	AND.W	D2,$5DBE(A4)
	RTS

	OR.W	D4,(A4)+
	OR.W	D4,$1F3E(A4)
	OR.W	D4,$3E7E(A4)
	AND.W	D2,$5DBE(A4)
	RTS

	AND.W	D2,(A4)+
	AND.W	D2,$1F3E(A4)
	AND.W	D2,$3E7E(A4)
	OR.W	D4,$5DBE(A4)
	RTS

	OR.W	D4,(A4)+
	AND.W	D2,$1F3E(A4)
	AND.W	D2,$3E7E(A4)
	OR.W	D4,$5DBE(A4)
	RTS

	AND.W	D2,(A4)+
	OR.W	D4,$1F3E(A4)
	AND.W	D2,$3E7E(A4)
	OR.W	D4,$5DBE(A4)
	RTS

	OR.W	D4,(A4)+
	OR.W	D4,$1F3E(A4)
	AND.W	D2,$3E7E(A4)
	OR.W	D4,$5DBE(A4)
	RTS

	AND.W	D2,(A4)+
	AND.W	D2,$1F3E(A4)
	OR.W	D4,$3E7E(A4)
	OR.W	D4,$5DBE(A4)
	RTS

	OR.W	D4,(A4)+
	AND.W	D2,$1F3E(A4)
	OR.W	D4,$3E7E(A4)
	OR.W	D4,$5DBE(A4)
	RTS

	AND.W	D2,(A4)+
	OR.W	D4,$1F3E(A4)
	OR.W	D4,$3E7E(A4)
	OR.W	D4,$5DBE(A4)
	RTS

	OR.W	D4,(A4)+
	OR.W	D4,$1F3E(A4)
	OR.W	D4,$3E7E(A4)
	OR.W	D4,$5DBE(A4)
	RTS

;======================================================================

ulRenderMaskedGraphicsObject:
	MOVE.L	D5,-(SP)
	MOVE.W	D1,-(SP)
	MOVEM.L	A4-A6,-(SP)
	AND.W	#$00FF,D0
	move.w	d0,d5
	ASL.W	#$02,D0
	MOVE.L	#graphicsPointerTable,A1
	MOVE.L	$00(A1,D0.W),A1
	ASL.W	#$02,D0
	MOVE.L	#graphicsRenderingParameters,A2
	LEA	$04(A2,D0.W),A2
	MOVE.W	$0004(A2),D0
	MOVE.W	$0006(A2),D3
	MOVE.L	renderFrameBuffer,A0
	cmp.w	#$33,d5					; added: render directly to chip if message background or top bar
	beq.s	.copyChip
	cmp.w	#16,d3
	bcs.s	.copyChip
	lea	fastRenderBuffer,a0
.copyChip:
		jmp	O+$69f74

;======================================================================

ulVerticalBlank:
	tst.b	creakingSoundCooldownTimer			; added
	beq.s	.creakingSoundCooldownTimerOk
	sub.b	#1,creakingSoundCooldownTimer
.creakingSoundCooldownTimerOk:
	add.b	#1,framesSinceCopperlistUpdateAccumulator
	CLR.W	D1
	CLR.W	D2
	TST.B	framesToWait
		rts

;======================================================================
; The patch table: each entry is the site, its length and what goes there.

PATCH		macro
		dc.l	O+\1
		dc.w	\2-\1
_ps		set	*
_pl		set	\2-\1
		endm
PATCHC		macro				;in chip memory, where the program stays
		dc.l	\1
		dc.w	\2-\1
_ps		set	*
_pl		set	\2-\1
		endm
ENDP		macro
		ifgt	*-_ps-_pl
		fail	"patch longer than its site"
		endc
		dcb.w	(_pl-(*-_ps))/2,$4e71
		endm
; A branch in the original's code, assembled here: \1 the condition code,
; \2 its address, \3 the target.
BRANCH		macro
		dc.w	$6000|(\1<<8),\3-(\2+2)
		endm

		cnop	0,2
patchTable
		PATCHC	$e82e,$e832		;copper list: no interrupt at line $fa
		dc.w	$ffff,$fffe
		ENDP
		PATCH	$f0dc,$f0e2
		jmp	verticalBlankInterrupt
		ENDP
		PATCH	$f112,$f118
		jmp	copperInterrupt
		ENDP
		PATCHC	$e74a,$e74e		;not Unleashed: its copper list starts with
		dc.w	$0801,$fffe		;a wait for line 8, which gives the VBlank
		ENDP				;interrupt time to swap the frame buffers
		PATCH	$ee44,$ee4a		;before the copper loads the pointers. The
		movea.l	#$e74a,a0		;chip original's start-up jmp, which never
		ENDP				;runs, gives way to it.
		PATCH	$1b7b6,$1b7bc
		jmp	setupFrameBufferAddresses
		ENDP
		PATCH	$1bace,$1bad4
		jmp	copyMainGameBackground
		ENDP
		PATCH	$595fc,$59602
		jsr	ulCharacterBuffer
		ENDP
		PATCH	$5990a,$59910		;lbC04B1EE: the key tables, not through pointers
	lea	uppercaseTable,a0		; added
		ENDP
		PATCH	$59914,$5991a
	lea	lowercaseTable,a0		; added
		ENDP
		PATCH	$5a7f4,$5a7fa		;animateDrawBridge
		rts
		ENDP
		PATCH	$5a7fe,$5a804
		jmp	ulDrawBridgeInactive
		ENDP
		PATCH	$5b346,$5b34a		;handleRaceStartCountdown
		MOVE.B	#$28,D0					; originally $2C
		ENDP
		PATCH	$5b354,$5b358
		MOVE.B	#$D8,D0					; originally $D4
		ENDP
		PATCH	$5b366,$5b36c
		jmp	ulDecrementTimer
		ENDP
		PATCH	$5b4a8,$5b4ac		;updateRaceStartRoll
		MOVE.B	#$0C,D4						; originally $10
		ENDP
		PATCH	$5b4b8,$5b4bc
		MOVE.B	#$F4,D4						; originally $F0
		ENDP
		PATCH	$5c280,$5c286		;calculateLateralTrackPosition
		MOVE.B	#$FF,D0					; originally $000000FF
		ENDP
		PATCH	$5d484,$5d49c		;mainGameLoop
		jsr	ulPhysicsLoop
		ENDP
		PATCH	$5d4fc,$5d502
		jsr	ulRaceOver
		ENDP
		PATCH	$5d558,$5d560
		CMP.B	#MAJOR_IMPACT_COOLDOWN_TIME,majorImpactCooldownTimer
		ENDP
		PATCH	$5d5e2,$5d5e8
		jsr	ulRestartCountdown
		ENDP
		PATCH	$5d5ec,$5d5f2
		jsr	ulRestartCountdownAdd
		ENDP
		PATCH	$5da54,$5da5e		;handlePause
		jsr	ulPauseMessage
		ENDP
		PATCH	$5da72,$5da78
		jsr	ulPauseMessageDone
		ENDP
		PATCH	$5dadc,$5dae4		;swapDisplayBuffers
		MOVE.B	#$00,framesToWait	; originally $06
		ENDP
		PATCH	$5db62,$5db72		;updateFrameThrottlingAndTimers
		jmp	ulLapTimeDisplay
		ENDP
		PATCH	$5dd6a,$5dd6e		;handleLapCompletionTiming
		MOVE.B	#$1B*FRAMERATE_MULTIPLIER,D0				; originally $1B
		ENDP
		PATCH	$5db9e,$5dba4		;updateFrameThrottlingAndTimers: updateLapTimer
		jsr	ulUpdateLapTimer
		ENDP
		PATCH	$5dbae,$5dbb4
		jsr	ulUpdateLapTimer
		ENDP
		PATCH	$5dfb4,$5dfba
		jmp	updateDamageAndTimers
		ENDP
		PATCH	$602b6,$602be		;handleOffTrack
		MOVE.B	#$10*FRAMERATE_MULTIPLIER,restartTimerCountdown			; originally $10
		ENDP
		PATCH	$60762,$6076a		;initializePlayerAtSegment
		MOVE.B	#$08/FRAMERATE_MULTIPLIER,chainLiftVelocity		; originally $08
		ENDP
		PATCH	$60824,$6082a
		jmp	ulUpdateBoostFuelDisplay
		ENDP
		PATCH	$60c92,$60c9a
		jmp	handleGroundCollision
		ENDP
		PATCH	$60cf8,$60d00
		jmp	handleEdgeCollision
		ENDP
		PATCH	$60f5a,$60f64
		jmp	renderDustCloud
		ENDP
		PATCH	$60fe0,$60fe2		;updateWheelSpeed
		LSR.W	#$05,D0			; originally $02
		ENDP
		PATCH	$611ce,$611d4		;updateCameraAngle
		jsr	ulCameraAngleY
		ENDP
		PATCH	$616dc,$616e6
		jsr	ulVerticalBlank
		ENDP
		PATCH	$6180e,$61812
		MOVE.W	#$0114*FRAMERATE_MULTIPLIER,D3	; originally $0114
		ENDP
		PATCH	$620ac,$620b4		;updateGamePhysics
		MOVE.B	#$05*FRAMERATE_MULTIPLIER,impactSoundCooldownTimer		; originally $05
		ENDP
		PATCH	$62138,$6213e
		jmp	updateVelocityDamping
		ENDP
		PATCH	$638e0,$638e4		;updateOpponentLateralPosition
		MOVE.B	#$FF,D0				; originally $F7
		ENDP
		PATCH	$638e4,$638e8
		BRANCH	0,$638e4,$638f4			; originally BNE
		ENDP
		PATCH	$638f0,$638f4
		MOVE.B	#$01,D0				; originally $09
		ENDP
		PATCH	$63cf0,$63cf8
		MOVE.B	#$03*FRAMERATE_MULTIPLIER,opponentCollisionTimer	; originally $03
		ENDP
		PATCH	$63dd2,$63ddc
		jsr	ulOpponentCollisionDamage
		ENDP
		PATCH	$63ed4,$63edc		;applyOpponentCollisionForces
		MOVE.B	#$05*FRAMERATE_MULTIPLIER,collisionSoundCooldown	; originally $05
		ENDP
		PATCH	$64532,$64538
		jsr	ulDisplayMenuScreen
		ENDP
		PATCH	$64f80,$64f8a		;processGameFrame
		jsr	ulSetupRendering
		ENDP
		PATCH	$651b0,$651b6
		jmp	ulGameFrameDone
		ENDP
		PATCH	$662c8,$662cc		;updateChainAnimation
		BRANCH	3,$662c8,$66346		; originally BEQ
		ENDP
		PATCH	$662d8,$662e0
		ADD.B	#$08/FRAMERATE_MULTIPLIER,chainLiftVelocity		; originally $08
		ENDP
		PATCH	$66348,$6634e
		jmp	setPixelColor
		ENDP
		PATCH	$663f2,$663f8
		jmp	plotPixel
		ENDP
		PATCH	$6646e,$66474
		jmp	applyBitplaneMask
		ENDP
		PATCH	$69f42,$69f4a
		jmp	ulRenderMaskedGraphicsObject
		ENDP
		PATCH	$6a0de,$6a0e4		;renderGraphicsObjectAtPosition
		lea	fastRenderBuffer,a0
		ENDP
		PATCH	$6a0ea,$6a0ec		;not Unleashed: a left edge off the screen
		ASR.L	#$03,D0			;moves a0 back, in any memory (originally
		ENDP				;LSR.L: the 24-bit address wraps)
		PATCH	$69fea,$69ff0		;not Unleashed: the game's own code where
		SWAP	D0			;the slave without the enhanced framerate,
		MOVE.W	#$FFFF,D0		;and TNT's patch, mask a0 to 24 bits
		ENDP
		PATCH	$6a06e,$6a074
		ADDA.L	#$00000002,A0
		ENDP
		PATCH	$5db3e,$5db42		;updateFrameThrottlingAndTimers
		MOVE.B	#TIMESTEP_FACTOR,D0
		ENDP
TIMESTEP	macro				;MOVE.B #$EE,D2: the physics steps
		PATCH	\1,\1+4
		MOVE.B	#TIMESTEP_FACTOR,D2
		ENDP
		endm
		TIMESTEP	$5b4be
		TIMESTEP	$61956
		TIMESTEP	$61972
		TIMESTEP	$6198e
		TIMESTEP	$619c0
		TIMESTEP	$619d8
		TIMESTEP	$619f0
		TIMESTEP	$61ae2
		TIMESTEP	$61afa
		TIMESTEP	$61b12
		TIMESTEP	$61b2c
		TIMESTEP	$61b44
		TIMESTEP	$61b5c
		TIMESTEP	$639f8
		TIMESTEP	$63be4
		TIMESTEP	$640f2
		TIMESTEP	$6410a
		TIMESTEP	$64124
		TIMESTEP	$6413c
		TIMESTEP	$64156
		TIMESTEP	$6416e
		dc.l	0

;======================================================================

		cnop	0,4
ulBss
fastRenderBuffer	= ulBss			;40*200*4, in fast memory
infiniteBoost		= ulBss+$7d00
plotPixelOffset		= ulBss+$7d04
framesSinceCopperlistUpdate	= ulBss+$7d06
framesSinceCopperlistUpdateAccumulator	= ulBss+$7d07
framesToProcess		= ulBss+$7d08
creakingSoundCooldownTimer	= ulBss+$7d09
grindSoundCooldownTimer	= ulBss+$7d0a
ulBssEnd		= ulBss+$7d0c
