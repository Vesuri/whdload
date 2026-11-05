; Plan step F: drive step C's manoeuvres on the Amiga. Private builds only
; (tools/build_feel.py includes this at the end of a copy of HardDrivinHD.s,
; with VERIFY_DRIVE and VERIFY_STEPINPUT; never part of a release). It sits
; at the end so that it moves no other code: the slave's PC-relative
; references to _resload are near their limit. HardDrivinVerify.s reaches it
; through the FEEL_CALL trampolines that build_feel.py adds there.
;
; At native race entry the car is moved to the open grass north of the start
; straight (FEEL_SEED_X/Z, generated), facing the start's heading 360 (+x).
; The grass behaves as road, as the arcade runs made their grass into road:
; build_feel.py patches $b762 so the engine never takes the grass branch (road
; drag, no off-road throttle loss) and $b146 so the off-road deadline never
; starts. Contact stays the native off-road (flat ground) contact.
; The ground must stay near the course: the road cursor G($98e4) scores road
; sections by sums of 16-bit relative coordinates, and more than about 16,000
; units from the sections it searches it takes garbage and the game crashes
; ($0c09a, address error). So the run ends (FEEL_DONE 4) when the car leaves
; FEEL_X_MIN..FEEL_X_MAX by FEEL_Z_MIN..FEEL_Z_MAX, within about 10,000 units
; of the flat start straight and its curves.
;
; The driver only supplies native input, like a player: mouse X for steering
; and the buttons for the throttle (4 raises it by 2 per native step, 1 lowers
; it) and the brake (5). Each VBL it publishes mouse X, Y 200 and the buttons,
; and the controls pass ($7c36) republishes them because it clears its latch.
; Arcade handling's mouse pedals (CUSTOM1=2) read the held buttons from
; _handling_pad instead: 4 holds the right button (gas), 1 releases it, 5
; holds the left (brake) alone at full pedal (pad bit 3, as a double click),
; and 0 keeps the gas as it was, so the gas pedal moves by 10 a field towards
; the throttle the driver aims at.
; - Speeds are in the native speedometer's scale, 0.28 MPH per unit of
;   G($9928); with arcade handling (CUSTOM1=2), whose world unit is 0.1791 ft
;   instead of E1's first 0.3504, _feel_velocity rescales G($9928) by
;   1/1.956 and the seed by 1.956, so the plans' MPH are real there.
; - Cruise holds the native velocity G($9928) at the target MPH / 0.28 (E1;
;   the speedometer comes from the RPM, lags in acceleration and at idle jumps
;   between 3 and 7 MPH). It aims the throttle at an estimate of the throttle
;   that holds the target plus 1 per unit of velocity error (3.6 per MPH), and
;   moves the throttle there with buttons 4 and 1 (none within 1). The
;   estimate starts at target / 3 and integrates the error while it is within
;   36 units (10 MPH). More than 11 units (3 MPH) too fast brakes (5), and so
;   does more than 4 too fast with the throttle shut.
; - Heading hold steers half the heading error to 360, at most 3 native
;   units, which never halves the turn or starts a skid up to 100 MPH.
; - The plan (_feel_plan, generated) is a list of t.w, op.w, a.w, b.w: entries
;   whose time has come run in order. t counts fields from the engine start or
;   from the end of the last wait. FE_SETTLE waits until the velocity has been
;   within 4 units (1.1 MPH) of the cruise target, and the heading within 1 unit
;   when held, for a fields, or until t reaches b (the original's low speeds
;   never hold: its velocity cycles); FE_STOP until the car has stood still
;   for a fields. Mouse offsets are X - 320.
;
; A crash or recovery ends the run (FEEL_DONE 2), as does a wait that lasts
; FEEL_T_MAX fields (3) or leaving the ground (4).
;
; Plan step H2 adds laps of the real course (FEEL_PATH 1, build_feel.py's
; lap plans): the car stays at the native start (FEEL_SEED_X 0), or starts
; on the stunt road at speed (FEEL_SEED_STUNT, FEEL_SEED_V), the ground
; keeps its native off-road rules, and FE_FOLLOW steers along _feel_path, a
; route through the road sections' centres every 50 units with a speed for
; each point. The steering is pure pursuit: aim at the point k ahead, k from
; the speed (_feel_gain), and steer the curvature that reaches it, scaled by
; the understeer at that speed. The cruise target is the aim point's speed.
; Crashes, replays and recoveries run their course with the buttons
; released, from a crash until its recovery (a held button skips the
; replay), and whenever 40 fields pass without a physics pass (an A500
; frame near the start can take 17),
; and after them the driver finds its place on the route again.
;
; The log: each VBL appends an 80-byte record to _feel_vbuf, and each
; physics pass a 92-byte pose to _feel_pbuf (race field, the fields the
; enhanced physics has consumed, then G($98fc)..G($994f)), so that poses are
; complete while a VBL can fall in the middle of a pass, and the first 80
; bytes of the arcade handling model's state to _feel_mbuf (HDFEEL03). The
; original build's pass ends at $10f28 (patched here); the enhanced build's
; at _dispatch_after_physics, whose own patch of $10f28 replaces this one.
; When a buffer is full, or the run ends, the driver calls its flush
; routine, where the capture's breakpoint appends the buffer to a file: one
; debugger stop per 32 entries keeps the capture fast.

	INCLUDE "feel_plan_equ.i"

FE_END		equ 0
FE_CRUISE	equ 1		; a = target MPH, 0 off
FE_HEAD		equ 2		; a = 1 hold heading 360, 0 off
FE_MOUSE	equ 3		; a = mouse offset
FE_RAMP		equ 4		; a = mouse offset at the end, b = fields
FE_BUTTONS	equ 5		; a = buttons, -1 for cruise's choice
FE_SETTLE	equ 6		; a = fields, b = give up at this t
FE_STOP		equ 7		; a = fields
FE_FOLLOW	equ 8		; a = 1 follow _feel_path, 0 off

FEEL_RECSIZE	equ 80		; record in _feel_vbuf
FEEL_EVENT	equ 0		; next plan entry
FEEL_T		equ 4
FEEL_COUNT	equ 6		; fields a wait's condition has held
FEEL_CRUISE	equ 8		; target MPH
FEEL_HEAD	equ 10
FEEL_MOUSE	equ 12
FEEL_RAMP_T0	equ 14		; -1: no ramp
FEEL_RAMP_FROM	equ 16
FEEL_RAMP_TO	equ 18
FEEL_RAMP_LEN	equ 20
FEEL_BUTTONS	equ 22
FEEL_X		equ 24		; published mouse X
FEEL_B		equ 26		; published buttons
FEEL_DONE	equ 28
FEEL_PHASE	equ 30		; 0 engine start, 1 plan
FEEL_TEQ	equ 32		; cruise's holding throttle, Q8
FEEL_VCOUNT	equ 34		; records in _feel_vbuf
FEEL_PCOUNT	equ 36		; poses in _feel_pbuf
FEEL_CRUISE_V	equ 38		; target velocity
FEEL_FOLLOW	equ 40		; following _feel_path
FEEL_IDX	equ 42		; nearest point of _feel_path
FEEL_LASTPASS	equ 44		; race field of the last physics pass, low word
FEEL_WAITREC	equ 46		; a crash: hands off until its recovery
FEEL_PED	equ 48		; arcade handling: the gas pedal as the buttons move it
FEEL_N		equ 32		; entries per buffer
FEEL_POSESIZE	equ 92
FEEL_MODELSIZE	equ 80		; _handling_state's first bytes, after each pass

; Race entry, from _verify_drive_race: place the car, reset the driver.
_feel_seed:
	movem.l d0/a0-a1,-(a7)
	lea _feel_state(pc),a0		; the driver steers as the arcade's wheel
	adda.l #_handling_curve-_feel_state,a0
	clr.w (a0)
	IFNE FEEL_SEED_X
	move.w #FEEL_SEED_X,d0
	move.w d0,-$6716(a4)		; camera G($98ea)
	move.w d0,-$670a(a4)		; pose G($98f6)
	move.l #FEEL_SEED_X*8,-$6704(a4)	; long pose G($98fc)
	IFNE FEEL_SEED_Y
	; on a raised section (a seeded route's first point): its centre height
	move.w #FEEL_SEED_Y,-$6714(a4)	; G($98ec)
	move.w #FEEL_SEED_Y,-$6708(a4)	; G($98f8)
	move.l #FEEL_SEED_Y*8,-$6700(a4)	; G($9900)
	ELSE
	clr.w -$6714(a4)		; G($98ec)
	clr.w -$6708(a4)		; G($98f8)
	clr.l -$6700(a4)		; G($9900)
	ENDC
	move.w #FEEL_SEED_Z,d0
	move.w d0,-$6712(a4)		; G($98ee)
	move.w d0,-$6706(a4)		; G($98fa)
	move.l #FEEL_SEED_Z*8,-$66fc(a4)	; G($9904)
	move.w #FEEL_SEED_HEAD,-$66bc(a4)	; angles G($9944..$994e)
	clr.l -$66ba(a4)
	move.w #FEEL_SEED_HEAD,-$66b6(a4)
	clr.l -$66b4(a4)
	clr.l -$66ec(a4)		; roll and pitch rates G($9914/$9916)
	clr.w -$66e6(a4)		; spin G($991a)
	clr.w -$66f2(a4)		; fall G($990e)
	move.b #15,-$66f0(a4)		; all wheels in contact G($9910)
	ENDC
	IFNE FEEL_SEED_V
	; already moving, in fourth, as the step 4 course probes seeded it
	move.w #FEEL_SEED_V,-$66d8(a4)	; velocity G($9928)
	lea _feel_state(pc),a0
	adda.l #_contact_arcade-_feel_state,a0
	tst.w (a0)
	beq.s .seed_v
	move.w #(FEEL_SEED_V*1956+500)/1000,-$66d8(a4)
.seed_v:
	move.w #5000,-$66d6(a4)		; RPM G($992a)
	move.w #111,-$66d4(a4)		; speedometer G($992c)
	move.w #396,-$66da(a4)		; G($9926)
	move.w #4,-$66ca(a4)		; gear G($9936)
	st -$66c2(a4)			; automatic G($993e)
	move.b #100,-$66e4(a4)		; throttle G($991c)
	lea -$68a6(a4),a0		; fourth gear's table G($9940)
	move.l a0,-$66c0(a4)
	ENDC
	IFNE FEEL_SEED_STUNT
	move.b #1,-$66b0(a4)		; on the stunt road G($9950)
	movea.l -$66ae(a4),a0		; its sections G($9952)
	adda.w #FEEL_SEED_SEGMENT*20,a0
	move.l a0,-$671c(a4)		; road cursor G($98e4)
	movea.l -$666c(a4),a0		; its waypoints G($9994)
	adda.w #FEEL_SEED_WAYPOINT*8,a0
	move.l a0,-$5230(a4)		; next waypoint G($add0)
	ENDC
	IFNE FEEL_SEED_MAIN
	; on the main road: only the road cursor (the next waypoint stays the
	; start's, so the race's progress messages are wrong)
	clr.b -$66b0(a4)		; G($9950)
	movea.l -$6720(a4),a0		; main road sections G($98e0)
	adda.w #FEEL_SEED_SEGMENT*20,a0
	move.l a0,-$671c(a4)		; road cursor G($98e4)
	ENDC
	lea _feel_state(pc),a0
	lea _feel_plan(pc),a1
	move.l a1,FEEL_EVENT(a0)
	clr.l FEEL_T(a0)		; T, COUNT
	clr.l FEEL_CRUISE(a0)		; CRUISE, HEAD
	clr.w FEEL_MOUSE(a0)
	move.w #-1,FEEL_RAMP_T0(a0)
	move.w #-1,FEEL_BUTTONS(a0)
	move.w #320,FEEL_X(a0)
	move.w #1,FEEL_B(a0)
	clr.l FEEL_DONE(a0)		; DONE, PHASE
	clr.w FEEL_TEQ(a0)
	clr.l FEEL_VCOUNT(a0)		; VCOUNT, PCOUNT
	clr.w FEEL_CRUISE_V(a0)
	clr.w FEEL_FOLLOW(a0)
	move.w #FEEL_START_IDX,FEEL_IDX(a0)
	clr.l FEEL_LASTPASS(a0)		; LASTPASS, WAITREC
	movem.l (a7)+,d0/a0-a1
	rts

; Controls entry: republish this field's input. Outside the race, hold
; button 4 as VERIFY_STEPINPUT does: that is what ends the attract demo.
_feel_input:
	move.l a0,-(a7)
	lea _feel_state(pc),a0
	adda.l #_verify_drive_state-_feel_state,a0
	cmpi.w #2,(a0)
	beq.s .race
	move.l #(320<<16)|200,-$6a06(a4)
	move.w #4,-$6a0a(a4)
	bra.s .done
.race:
	lea _feel_state(pc),a0
	move.w FEEL_X(a0),-$6a06(a4)
	move.w #200,-$6a04(a4)
	move.w FEEL_B(a0),-$6a0a(a4)
.done:
	movea.l (a7)+,a0
	rts

; VBL during the race: advance the driver, publish its input, record.
_feel_vbl:
	movem.l d0-d3/a0-a2,-(a7)
	lea _feel_state(pc),a2
	move.w FEEL_DONE(a2),-(a7)	; nonzero: ended in an earlier field
	tst.w FEEL_DONE(a2)
	bne .publish
	tst.b -$69fa(a4)		; crash G($9606)
	bne .spoilt
	tst.b -$69fb(a4)		; recovery G($9605)
	bne .spoilt
	IFNE FEEL_PATH
	tst.w FEEL_WAITREC(a2)		; the replay between a crash and its recovery
	bne .stop
	tst.w FEEL_PHASE(a2)
	beq.s .bounded
	lea _feel_state(pc),a0		; a replay: no physics pass for 40 fields
	adda.l #_verify_drive_state-_feel_state,a0
	move.w 6(a0),d0
	sub.w FEEL_LASTPASS(a2),d0
	cmpi.w #40,d0
	bhi .stop
	bra.s .bounded
	ENDC
	move.l -$6704(a4),d0		; long pose x, z G($98fc/$9904)
	cmpi.l #FEEL_X_MIN*8,d0
	blt.s .left
	cmpi.l #FEEL_X_MAX*8,d0
	bgt.s .left
	move.l -$66fc(a4),d0
	cmpi.l #FEEL_Z_MIN*8,d0
	blt.s .left
	cmpi.l #FEEL_Z_MAX*8,d0
	bgt.s .left
.bounded:
	tst.w FEEL_PHASE(a2)
	bne.s .plan
	; any button starts the engine; 1 leaves the zero throttle alone
	tst.b -$5224(a4)		; throttle enabled G($addc)
	beq .publish
	move.w #1,FEEL_PHASE(a2)
	clr.l FEEL_T(a2)
.plan:
	bsr _feel_events
	tst.w FEEL_DONE(a2)
	bne.s .stop
	bsr _feel_outputs
	bsr _feel_pad
	addq.w #1,FEEL_T(a2)
	cmpi.w #FEEL_T_MAX,FEEL_T(a2)
	blo .publish
	move.w #3,FEEL_DONE(a2)
	bra.s .stop
.left:
	move.w #4,FEEL_DONE(a2)
	bra.s .stop
.spoilt:
	IFNE FEEL_PATH
	; crashes and recoveries run their course, and a crash's replay too (a
	; held button would skip it): hands off from the crash to its recovery
	move.w #1,FEEL_WAITREC(a2)
	tst.b -$69fb(a4)
	beq.s .stop
	clr.w FEEL_WAITREC(a2)
	bra.s .stop
	ENDC
	move.w #2,FEEL_DONE(a2)
.stop:
	move.w #320,FEEL_X(a2)
	clr.w FEEL_B(a2)
	lea _feel_state(pc),a0
	adda.l #_handling_pad-_feel_state,a0
	clr.w (a0)
	move.w #-1,_handling_gas-_handling_pad(a0)
.publish:
	move.w FEEL_X(a2),-$6a06(a4)
	move.w #200,-$6a04(a4)
	move.w FEEL_B(a2),-$6a0a(a4)
	tst.w (a7)+
	bne.s .out
	bsr _feel_record
.out:
	movem.l (a7)+,d0-d3/a0-a2
	rts

; D0.w = G($9928) in the native speedometer's scale (above).
_feel_velocity:
	move.w -$66d8(a4),d0		; velocity G($9928)
	move.l a0,-(a7)
	lea _feel_state(pc),a0
	adda.l #_contact_arcade-_feel_state,a0
	tst.w (a0)
	movea.l (a7)+,a0
	beq.s .done
	muls.w #16753,d0		; / 1.956
	add.l d0,d0
	swap d0
.done:
	rts

; The native buttons FEEL_B as the arcade pedals' held buttons (above).
_feel_pad:
	lea _feel_state(pc),a0
	adda.l #_handling_pad-_feel_state,a0
	move.w FEEL_B(a2),d0
	beq.s .keep
	moveq #12,d1			; 5: the brake alone, at full pedal
	cmpi.w #5,d0
	beq.s .pad
	moveq #1,d1			; 4: the gas
	cmpi.w #4,d0
	beq.s .pad
	moveq #0,d1			; 1: neither
.pad:
	move.w d1,(a0)
	rts
.keep:
	andi.w #1,(a0)
	rts

_feel_events:
	movea.l FEEL_EVENT(a2),a0
.next:
	move.w (a0),d0
	cmp.w FEEL_T(a2),d0
	bgt .done
	move.w 2(a0),d0
	move.w 4(a0),d1
	move.w 6(a0),d2
	tst.w d0
	beq .end
	subq.w #FE_CRUISE,d0
	beq .cruise
	subq.w #FE_HEAD-FE_CRUISE,d0
	beq .head
	subq.w #FE_MOUSE-FE_HEAD,d0
	beq .mouse
	subq.w #FE_RAMP-FE_MOUSE,d0
	beq .ramp
	subq.w #FE_BUTTONS-FE_RAMP,d0
	beq .buttons
	subq.w #FE_SETTLE-FE_BUTTONS,d0
	beq .settle
	subq.w #FE_FOLLOW-FE_SETTLE,d0
	beq .follow
	; FE_STOP
	tst.w -$66d8(a4)		; velocity G($9928)
	bne .wait
	tst.w -$66d4(a4)		; speedometer G($992c)
	bne .wait
	bra .held
.end:
	move.w #1,FEEL_DONE(a2)
	bra .done
.cruise:
	move.w d1,FEEL_CRUISE(a2)
	move.w d1,d0
	mulu.w #100,d0
	addi.l #14,d0
	divu.w #28,d0
	move.w d0,FEEL_CRUISE_V(a2)
	mulu.w #85,d1
	move.w d1,FEEL_TEQ(a2)
	bra .advance
.head:
	move.w d1,FEEL_HEAD(a2)
	bra .advance
.follow:
	move.w d1,FEEL_FOLLOW(a2)
	bra .advance
.mouse:
	move.w d1,FEEL_MOUSE(a2)
	move.w #-1,FEEL_RAMP_T0(a2)
	bra .advance
.ramp:
	move.w FEEL_MOUSE(a2),FEEL_RAMP_FROM(a2)
	move.w d1,FEEL_RAMP_TO(a2)
	move.w d2,FEEL_RAMP_LEN(a2)
	move.w FEEL_T(a2),FEEL_RAMP_T0(a2)
	bra .advance
.buttons:
	move.w d1,FEEL_BUTTONS(a2)
	bra .advance
.settle:
	cmp.w FEEL_T(a2),d2
	ble .settled
	bsr _feel_velocity
	sub.w FEEL_CRUISE_V(a2),d0
	bpl .speed
	neg.w d0
.speed:
	cmpi.w #4,d0
	bgt .wait
	tst.w FEEL_HEAD(a2)
	beq .held
	move.w -$66b6(a4),d0		; heading G($994a)
	subi.w #360,d0
	bpl .heading
	neg.w d0
.heading:
	cmpi.w #1,d0
	bgt .wait
.held:
	addq.w #1,FEEL_COUNT(a2)
	cmp.w FEEL_COUNT(a2),d1
	bgt .done
.settled:
	; the condition held long enough (or the wait gave up): the clock restarts
	clr.l FEEL_T(a2)
.advance:
	addq.l #8,a0
	bra .next
.wait:
	clr.w FEEL_COUNT(a2)
.done:
	move.l a0,FEEL_EVENT(a2)
	rts

_feel_outputs:
	IFNE FEEL_PATH
	tst.w FEEL_FOLLOW(a2)
	beq.s .not_following
	bsr _feel_follow
	bra .x
.not_following:
	ENDC
	tst.w FEEL_HEAD(a2)
	beq.s .manual
	move.w #360,d0
	sub.w -$66b6(a4),d0		; within -360..1080
	cmpi.w #720,d0
	ble.s .wrapped
	subi.w #1440,d0
.wrapped:
	ext.l d0
	divs.w #2,d0
	cmpi.w #3,d0
	ble.s .below
	moveq #3,d0
.below:
	cmpi.w #-3,d0
	bge.s .above
	moveq #-3,d0
.above:
	muls.w #20,d0
	bra.s .x
.manual:
	move.w FEEL_RAMP_T0(a2),d1
	bmi.s .fixed
	move.w FEEL_T(a2),d0
	sub.w d1,d0
	cmp.w FEEL_RAMP_LEN(a2),d0
	blt.s .ramping
	move.w FEEL_RAMP_TO(a2),FEEL_MOUSE(a2)
	move.w #-1,FEEL_RAMP_T0(a2)
	bra.s .fixed
.ramping:
	move.w FEEL_RAMP_TO(a2),d1
	sub.w FEEL_RAMP_FROM(a2),d1
	muls.w d1,d0
	divs.w FEEL_RAMP_LEN(a2),d0
	add.w FEEL_RAMP_FROM(a2),d0
	bra.s .x
.fixed:
	move.w FEEL_MOUSE(a2),d0
.x:
	addi.w #320,d0
	bpl.s .low
	moveq #0,d0
.low:
	cmpi.w #639,d0
	ble.s .high
	move.w #639,d0
.high:
	move.w d0,FEEL_X(a2)
	lea _feel_state(pc),a0		; the buttons move the gas, unless the
	adda.l #_handling_gas-_feel_state,a0 ; arcade cruise below sets it
	move.w #-1,(a0)
	move.w FEEL_BUTTONS(a2),d0
	bpl.s .buttons
	moveq #0,d0
	tst.w FEEL_CRUISE(a2)
	beq.s .buttons
	bsr _feel_velocity
	move.w FEEL_CRUISE_V(a2),d1
	sub.w d0,d1			; velocity error
	bsr _feel_arcade
	bne .arcade_cruise
	moveq #5,d0
	cmpi.w #-11,d1
	blt.s .buttons
	cmpi.w #-4,d1
	bge.s .slow_enough
	tst.b -$66e4(a4)		; too fast with the throttle shut
	beq.s .buttons
.slow_enough:
	move.w FEEL_TEQ(a2),d2
	cmpi.w #36,d1
	bgt.s .aim
	cmpi.w #-36,d1
	blt.s .aim
	add.w d1,d2
	bpl.s .teq_low
	moveq #0,d2
.teq_low:
	cmpi.w #100<<8,d2
	ble.s .teq_high
	move.w #100<<8,d2
.teq_high:
	move.w d2,FEEL_TEQ(a2)
.aim:
	asr.w #8,d2
	add.w d1,d2			; throttle to aim at
	moveq #0,d1
	move.b -$66e4(a4),d1		; throttle G($991c)
	bsr _feel_arcade
	beq.s .native_gas
	move.w FEEL_PED(a2),d1		; the pedal now, not at the last pass
.native_gas:
	sub.w d1,d2
	moveq #0,d0
	cmpi.w #1,d2
	ble.s .not_up
	moveq #4,d0
.not_up:
	cmpi.w #-1,d2
	bge.s .buttons
	moveq #1,d0
.buttons:
	move.w d0,FEEL_B(a2)
	; with arcade handling follow the gas pedal field by field, as
	; _handling_pedals moves it: G($991c) changes only once a pass, and
	; on the A500 aiming from it held the gas a whole pass and pumped it
	bsr _feel_arcade
	beq.s .pedal_done
	move.w FEEL_PED(a2),d1
	cmpi.w #4,d0
	bne.s .pedal_lift
	addi.w #HANDLING_PEDAL,d1
	cmpi.w #100,d1
	ble.s .pedal
	moveq #100,d1
	bra.s .pedal
.pedal_lift:
	tst.w d0
	beq.s .pedal_done		; 0 keeps the gas
	subi.w #HANDLING_GAS_LIFT,d1	; the gas lifts slower than it opens
	bpl.s .pedal
	moveq #0,d1
.pedal:
	move.w d1,FEEL_PED(a2)
.pedal_done:
	rts

; With arcade handling the cruise sets the gas pedal itself, every field, as
; step C's MAME plans did (hd.lua): pedal = integral + 0.08 per MPH of
; error, the integral moving 0.05 per MPH a second while the pedal is not
; held at an end by it. Per velocity unit (0.28 MPH) and field, of 100:
; 2.25 and 0.028 (Q8 7). The integral is FEEL_TEQ, Q8. D1 = velocity error.
.arcade_cruise:
	move.w d1,d0
	muls.w #9,d0
	asr.l #2,d0			; 2.25 per unit
	move.w FEEL_TEQ(a2),d2
	asr.w #8,d2
	add.w d0,d2			; the pedal the integral and error give
	tst.w d1
	bmi.s .ac_slower
	cmpi.w #100,d2
	bge.s .ac_pedal			; held open: no wind-up
	bra.s .ac_integrate
.ac_slower:
	tst.w d2
	ble.s .ac_pedal			; held shut
.ac_integrate:
	move.w d1,d2
	muls.w #7,d2
	add.w FEEL_TEQ(a2),d2
	bpl.s .ac_low
	moveq #0,d2
.ac_low:
	cmpi.w #100<<8,d2
	ble.s .ac_high
	move.w #100<<8,d2
.ac_high:
	move.w d2,FEEL_TEQ(a2)
.ac_pedal:
	move.w FEEL_TEQ(a2),d2
	asr.w #8,d2
	add.w d0,d2
	bpl.s .ac_open
	moveq #0,d2
.ac_open:
	cmpi.w #100,d2
	ble.s .ac_set
	moveq #100,d2
.ac_set:
	lea _feel_state(pc),a0
	adda.l #_handling_gas-_feel_state,a0
	move.w d2,(a0)
	move.w d2,FEEL_PED(a2)
	moveq #0,d0			; no buttons: the brake stays off
	move.w d0,FEEL_B(a2)
	rts

; Z clear with arcade handling (_contact_arcade set). Keeps D0-D2.
_feel_arcade:
	move.l a0,-(a7)
	lea _feel_state(pc),a0
	adda.l #_contact_arcade-_feel_state,a0
	tst.w (a0)
	movea.l (a7)+,a0
	rts

	IFNE FEEL_PATH
; FE_FOLLOW: D0 = the mouse offset that steers towards the route; sets the
; cruise target. A2 = state. Distances are |dx| + |dy| + |dz| in world
; units, from word differences, so the 16-bit wrap of the course's x does
; not matter.
_feel_follow:
	movem.l d1-d7/a0-a1,-(a7)
	lea _feel_path(pc),a0
	move.w -$670a(a4),d4		; pose x, y, z words G($98f6..$98fa)
	move.w -$6708(a4),d5
	move.w -$6706(a4),d6
	move.w FEEL_IDX(a2),d1
	bsr _feel_path_dist
	cmpi.l #1500,d0
	bls.s .near
	; lost, after a recovery: search 200 points either side
	move.w FEEL_IDX(a2),d1
	subi.w #200,d1
	bpl.s .from
	moveq #0,d1
.from:
	move.w FEEL_IDX(a2),d3
	addi.w #200,d3
	cmpi.w #FEEL_PATH_N-1,d3
	bls.s .to
	move.w #FEEL_PATH_N-1,d3
.to:
	move.w d3,a1
	move.l #$7fffffff,d7
.search:
	bsr _feel_path_dist
	cmp.l d7,d0
	bhs.s .worse
	move.l d0,d7
	move.w d1,FEEL_IDX(a2)
.worse:
	addq.w #1,d1
	cmp.w a1,d1
	bls.s .search
.near:
	; move on while the next point is no farther, at most 40 points
	move.w FEEL_IDX(a2),d1
	bsr _feel_path_dist
	move.l d0,d7
	moveq #39,d3
.advance:
	cmpi.w #FEEL_PATH_N-1,d1
	bhs.s .placed
	addq.w #1,d1
	bsr _feel_path_dist
	cmp.l d7,d0
	bls.s .closer
	subq.w #1,d1
	bra.s .placed
.closer:
	move.l d0,d7
	dbf d3,.advance
.placed:
	move.w d1,FEEL_IDX(a2)
	cmpi.w #FEEL_PATH_N-2,d1
	blo.s .going
	move.w #1,FEEL_DONE(a2)		; the end of the route
.going:
	; lookahead and gain for the speed
	bsr _feel_velocity
	ext.l d0
	bpl.s .forward
	moveq #0,d0
.forward:
	mulu.w #28,d0
	divu.w #8*100,d0		; MPH / 8
	cmpi.w #FEEL_GAIN_N-1,d0
	bls.s .bin
	moveq #FEEL_GAIN_N-1,d0
.bin:
	lsl.w #2,d0
	lea _feel_gain(pc),a1
	move.w 2(a1,d0.w),d7		; gain, Q8
	; points marked straight (bit 15 of the speed: the loop) are driven
	; with the wheel centred, and never aimed at from outside them
	move.w d1,d3
	lsl.w #3,d3
	tst.w 6(a0,d3.w)
	bpl.s .free
	moveq #0,d7
.free:
	move.w d1,d5			; the nearest point (the car's y is done with)
	add.w (a1,d0.w),d1		; the aim point
	cmpi.w #FEEL_PATH_N-1,d1
	bls.s .aim
	move.w #FEEL_PATH_N-1,d1
.aim:
	tst.w d7
	beq.s .aimed
	move.w d1,d3
	lsl.w #3,d3
	tst.w 6(a0,d3.w)
	bpl.s .aimed
	subq.w #1,d1
	cmp.w d5,d1
	bhi.s .aim
.aimed:
	lsl.w #3,d1
	move.w 6(a0,d1.w),d3		; its speed, MPH
	bclr #15,d3
	move.w (a0,d1.w),d2
	sub.w d4,d2			; dx
	move.w 4(a0,d1.w),d4
	sub.w d6,d4			; dz
	; the aim point ahead of the car, f = dx sin + dz cos, and to its
	; right, e = dx cos - dz sin (sin and cos Q14)
	move.w d2,d0
	muls.w -$6bb8(a4),d0		; sin G($9448)
	move.w d4,d6
	muls.w -$6bb6(a4),d6		; cos G($944a)
	add.l d6,d0
	moveq #14,d6
	asr.l d6,d0
	muls.w -$6bb6(a4),d2
	muls.w -$6bb8(a4),d4
	sub.l d4,d2
	asr.l d6,d2
	move.w #320,d4			; behind the car: full lock towards it
	tst.w d0
	ble .behind
	; the gain is for an aim point L ahead; scale by (L / D)^2 with D the
	; real distance, max + min / 2, and D at least L / 2
	lsr.w #3,d1
	sub.w d5,d1
	mulu.w #FEEL_SPACING,d1		; L
	cmpi.w #100,d1
	bhs.s .long
	moveq #100,d1
.long:
	move.w d2,d4
	bpl.s .e_abs
	neg.w d4
.e_abs:
	move.w d0,d6
	cmp.w d4,d6
	bls.s .octagon
	exg d4,d6
.octagon:
	lsr.w #1,d6
	add.w d6,d4			; D
	move.w d1,d6
	lsr.w #1,d6
	cmp.w d6,d4
	bhs.s .far
	move.w d6,d4
.far:
	muls.w d7,d2
	asr.l #8,d2
	cmpi.l #4000,d2
	ble.s .c_high
	move.l #4000,d2
.c_high:
	cmpi.l #-4000,d2
	bge.s .c_low
	move.l #-4000,d2
.c_low:
	muls.w d1,d2
	divs.w d4,d2
	ext.l d2
	muls.w d1,d2
	divs.w d4,d2
	ext.l d2
	cmpi.l #320,d2
	ble.s .right
	move.l #320,d2
.right:
	cmpi.l #-320,d2
	bge.s .left
	move.l #-320,d2
	bra.s .left
.behind:
	tst.w d7
	beq.s .centred
	tst.w d2
	bpl.s .full
	neg.w d4
.full:
	move.w d4,d2
	ext.l d2
	bra.s .left
.centred:
	moveq #0,d2
.left:
	cmp.w FEEL_CRUISE(a2),d3
	beq.s .target
	tst.w FEEL_CRUISE(a2)
	bne.s .retarget
	move.w d3,d0
	mulu.w #85,d0
	move.w d0,FEEL_TEQ(a2)
.retarget:
	move.w d3,FEEL_CRUISE(a2)
	mulu.w #100,d3
	addi.l #14,d3
	divu.w #28,d3
	move.w d3,FEEL_CRUISE_V(a2)
.target:
	move.l d2,d0
	movem.l (a7)+,d1-d7/a0-a1
	rts

; D0 = distance from the car (D4-D6) to point D1 of _feel_path (A0).
; Clobbers D2.
_feel_path_dist:
	move.w d1,d2
	lsl.w #3,d2
	move.w (a0,d2.w),d0
	sub.w d4,d0
	bpl.s .x
	neg.w d0
.x:
	swap d0
	move.w 2(a0,d2.w),d0
	sub.w d5,d0
	bpl.s .y
	neg.w d0
.y:
	move.w 4(a0,d2.w),d2
	sub.w d6,d2
	bpl.s .z
	neg.w d2
.z:
	add.w d2,d0			; |dy| + |dz| < 65536 near the route
	swap d0
	moveq #0,d2
	move.w d0,d2
	clr.w d0
	swap d0
	add.l d2,d0
	rts
	ENDC

; The record: race field, long pose, angles, engine, input, skid, movement
; vector, contact, road, crash, plan state, the remaining-time clock and the
; fields the enhanced physics has consumed (its game time; 0 with CUSTOM1=0).
_feel_record:
	move.w FEEL_VCOUNT(a2),d0
	mulu.w #FEEL_RECSIZE,d0
	lea _feel_vbuf(pc),a0
	adda.l d0,a0
	lea _feel_state(pc),a1
	adda.l #_verify_drive_state-_feel_state,a1
	move.l 4(a1),(a0)+		;  0 race field
	move.l -$6704(a4),(a0)+		;  4 G($98fc) x8
	move.l -$6700(a4),(a0)+		;  8 G($9900) y8
	move.l -$66fc(a4),(a0)+		; 12 G($9904) z8
	move.w -$66b6(a4),(a0)+		; 16 G($994a) heading
	move.w -$66b4(a4),(a0)+		; 18 G($994c)
	move.w -$66b2(a4),(a0)+		; 20 G($994e)
	move.w -$66d8(a4),(a0)+		; 22 G($9928) velocity
	move.w -$66d4(a4),(a0)+		; 24 G($992c) speedometer
	move.w -$66d6(a4),(a0)+		; 26 G($992a) RPM
	move.w -$66ca(a4),(a0)+		; 28 G($9936) gear
	move.b -$66e4(a4),(a0)+		; 30 G($991c) throttle
	move.b -$66ef(a4),(a0)+		; 31 G($9911) brake
	move.w FEEL_X(a2),(a0)+		; 32 mouse X
	move.w FEEL_B(a2),(a0)+		; 34 buttons
	move.w -$66e6(a4),(a0)+		; 36 G($991a) spin
	move.b -$50cf(a4),(a0)+		; 38 G($af31) skid
	move.b -$870(a4),(a0)+		; 39 G($f790) hard turn
	move.w -$66e2(a4),(a0)+		; 40 G($991e) movement x
	move.w -$66e0(a4),(a0)+		; 42 G($9920) movement y
	move.w -$66de(a4),(a0)+		; 44 G($9922) movement z
	move.b -$66f0(a4),(a0)+		; 46 G($9910) contact
	move.b -$16b6(a4),(a0)+		; 47 G($e94a) road
	move.b -$69fa(a4),(a0)+		; 48 G($9606) crash
	move.b -$69fb(a4),(a0)+		; 49 G($9605) recovery
	move.w -$66f2(a4),(a0)+		; 50 G($990e) fall
	move.l FEEL_EVENT(a2),d0
	lea _feel_plan(pc),a1
	sub.l a1,d0
	lsr.l #3,d0
	move.w d0,(a0)+			; 52 plan entry
	move.w FEEL_T(a2),(a0)+		; 54 plan time
	move.l -$6868(a4),(a0)+		; 56 G($9798) remaining time, BCD
	move.w FEEL_DONE(a2),(a0)+	; 60
	move.w FEEL_PHASE(a2),(a0)+	; 62
	move.w FEEL_BUTTONS(a2),(a0)+	; 64 plan buttons, -1 cruise
	move.w FEEL_CRUISE(a2),(a0)+	; 66
	move.w FEEL_HEAD(a2),(a0)+	; 68
	move.w -$66ec(a4),(a0)+		; 70 G($9914) roll rate
	move.w -$66ea(a4),(a0)+		; 72 G($9916) pitch rate
	lea _feel_state(pc),a1		; 74 fields the enhanced physics consumed
	adda.l #_dispatch_state-_feel_state,a1
	move.l DS_CONSUMED(a1),(a0)+
	move.w -$66bc(a4),(a0)+		; 78 G($9944)
	addq.w #1,FEEL_VCOUNT(a2)
	cmpi.w #FEEL_N,FEEL_VCOUNT(a2)
	beq.s .flush
	tst.w FEEL_DONE(a2)
	beq.s .kept
.flush:
	bsr _feel_flush_rec
	clr.w FEEL_VCOUNT(a2)
.kept:
	rts

; After each physics pass of the race: append the complete pose.
_feel_pass:
	movem.l d0/a0-a2,-(a7)
	lea _feel_state(pc),a0
	adda.l #_verify_drive_state-_feel_state,a0
	cmpi.w #2,(a0)
	bne .done
	lea _feel_state(pc),a2
	move.w FEEL_PCOUNT(a2),d0
	mulu.w #FEEL_POSESIZE,d0
	lea _feel_pbuf(pc),a1
	adda.l d0,a1
	move.l 4(a0),(a1)+		; race field
	move.w 6(a0),FEEL_LASTPASS(a2)
	; the pedal followed from the buttons drifts from the model's only
	; after a reset or the engine start: take the model's then
	moveq #0,d0
	move.b -$66e4(a4),d0		; throttle G($991c)
	sub.w FEEL_PED(a2),d0
	bpl.s .ped_diff
	neg.w d0
.ped_diff:
	cmpi.w #30,d0
	ble.s .ped_ok
	moveq #0,d0
	move.b -$66e4(a4),d0
	move.w d0,FEEL_PED(a2)
.ped_ok:
	lea _feel_state(pc),a0
	adda.l #_dispatch_state-_feel_state,a0
	move.l DS_CONSUMED(a0),(a1)+
	lea -$6704(a4),a0		; G($98fc)..G($994f)
	moveq #(FEEL_POSESIZE-8)/4-1,d0
.copy:
	move.l (a0)+,(a1)+
	dbf d0,.copy
	IFD VERIFY_HANDLING
	; the arcade handling model's state (zero unless CUSTOM1=2): v, r, the
	; load transfer, the heading, both axles, the step's inputs and outputs
	move.w FEEL_PCOUNT(a2),d0
	mulu.w #FEEL_MODELSIZE,d0
	lea _feel_mbuf(pc),a1
	adda.l d0,a1
	lea _feel_state(pc),a0
	adda.l #_handling_state-_feel_state,a0
	moveq #FEEL_MODELSIZE/4-1,d0
.model:
	move.l (a0)+,(a1)+
	dbf d0,.model
	ENDC
	addq.w #1,FEEL_PCOUNT(a2)
	cmpi.w #FEEL_N,FEEL_PCOUNT(a2)
	blo.s .done
	bsr _feel_flush_steps
	clr.w FEEL_PCOUNT(a2)
.done:
	movem.l (a7)+,d0/a0-a2
	rts

; Original build: $10f28 (through _feel_after_tramp), after the physics call,
; with its two displaced calls.
_feel_after_native:
	bsr _feel_pass
	jsr -$7fec(a4)			; game $00740
	move.l a0,-(a7)
	lea _feel_state(pc),a0
	adda.l #_code_start-_feel_state,a0
	movea.l (a0),a0
	adda.l #$e706,a0
	jsr (a0)
	movea.l (a7)+,a0
	rts

; The capture's breakpoints: it appends the buffer while stopped here.
_feel_flush_rec:
	nop
	rts
_feel_flush_steps:
	nop
	rts

	CNOP 0,4
_feel_signature:
	dc.b 'HDFEEL03'
	dc.l _feel_state-_feel_signature,_feel_vbuf-_feel_signature,_feel_pbuf-_feel_signature
	dc.l _feel_flush_rec-_feel_signature,_feel_flush_steps-_feel_signature
	dc.l _feel_mbuf-_feel_signature
_feel_state:
	dc.l 0
	dc.w 0,0,0,0,0,-1,0,0,0,-1,320,0,0,0,0,0,0,0,0,0,0,0,0
_feel_vbuf:
	dcb.b FEEL_N*FEEL_RECSIZE,0
_feel_pbuf:
	dcb.b FEEL_N*FEEL_POSESIZE,0
_feel_mbuf:
	dcb.b FEEL_N*FEEL_MODELSIZE,0

	INCLUDE "feel_plan.i"
