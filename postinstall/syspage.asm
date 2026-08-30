; The ROM's system page after MasterBASIC has installed itself.
;
; THIS IS NOT A VERIFIED LISTING.  disasm/ can be proved right by
; assembling it and comparing with the original file.  Nothing here can:
; there is no original to compare against.  Every byte below was either
; copied out of the image by a rule read from the installer, or is &FF
; standing for a byte this page holds that the file does not.
;
; What it is for: the code the ROM calls through CMDV, EDITV, RST8V,
; PRTOKV, EVALUV, FRAMIV, PATOUT and INSLV runs here, at these addresses,
; with MasterBASIC paged out.  In disasm/masterbasic.asm the same code
; sits at &7460 and &7BA4 and has to be read with a bias in your head.
;
; Operands that are zero are not necessarily zero in the running system.
; RESOLVE_ROM_ENTRIES fills several of them with ROM addresses it finds
; by signature before the installer copies the blocks out here.
;
; 791 bytes are reached as code from the eight vectors; 1092 bytes were
; placed in total.
;
; What is deliberately missing:
;
;   &45A2   PATCH_45A2 at &7800 copies a space skipper here out of the
;           DOS page tail, and the block below does JP Z,&45A2.  It is
;           not placed here because which page that copy lands in is not
;           settled -- nothing in that routine touches LMPR, which says
;           its own, but the code it installs reads &5A9A and &5C3C as
;           ROM system variables, which says this one.  See
;           notes/mb-selfpatch.txt.  A dump of the running machine would
;           decide it.
;
;   &4000-&46CB and &4AEC-&4B9F are the ROM's own heap and stack, with
;           BASIC's stack moved down to &45A1 by INSTALL_ROM_VECTORS.
;           Nothing of MasterBASIC's is placed there.
;
; The jumps that go to &0000 are the ones RESOLVE_ROM_ENTRIES fills in
; before the copy; the listing shows the zeros the file holds.
               ORG  &46CC

; --------------------------------------------------------------------
; first stub, from &7460
; --------------------------------------------------------------------

INSLV_TARGET:
               LD A,B                          ; 46CC 78
               AND A                           ; 46CD A7
               JR NZ,S46D6                     ; 46CE 20 06
               LD A,C                          ; 46D0 79
               CP &15                          ; 46D1 FE 15
               JP C,&0000                      ; 46D3 DA 00 00

; ---- S46D6 ---- from &46CE
S46D6:
               EX AF,AF'                       ; 46D6 08
               JR NC,S46E2                     ; 46D7 30 09
               EX AF,AF'                       ; 46D9 08
               LD HL,(&5AC8)                   ; 46DA 2A C8 5A
               EX DE,HL                        ; 46DD EB
               CALL S483A                      ; 46DE CD 3A 48
               EX AF,AF'                       ; 46E1 08

; ---- S46E2 ---- from &46D7
S46E2:
               EX AF,AF'                       ; 46E2 08

; ---- S46E3 ---- from &4700, &4722, &47B2
S46E3:
               LD A,(&5ACF)                    ; 46E3 3A CF 5A
               LD H,A                          ; 46E6 67
               IN A,(&FB)                      ; 46E7 DB FB
               XOR H                           ; 46E9 AC
               AND &1F                         ; 46EA E6 1F
               LD HL,(&5AC8)                   ; 46EC 2A C8 5A
               JP Z,S482D                      ; 46EF CA 2D 48
               LD A,B                          ; 46F2 78
               CP &20                          ; 46F3 FE 20
               JR C,S4702                      ; 46F5 38 0B
               SUB &1F                         ; 46F7 D6 1F
               LD B,A                          ; 46F9 47
               CALL S4702                      ; 46FA CD 02 47
               LD BC,&1F00                     ; 46FD 01 00 1F
               JR S46E3                        ; 4700 18 E1

; ---- S4702 ---- from &46F5, &46FA
S4702:
               EX AF,AF'                       ; 4702 08
               JP C,S478B                      ; 4703 DA 8B 47
               SBC HL,BC                       ; 4706 ED 42
               EX AF,AF'                       ; 4708 08
               INC HL                          ; 4709 23
               LD A,H                          ; 470A 7C
               CP &C0                          ; 470B FE C0
               JR NC,S4724                     ; 470D 30 15
               PUSH BC                         ; 470F C5
               LD B,H                          ; 4710 44
               LD C,L                          ; 4711 4D
               LD HL,&C001                     ; 4712 21 01 C0
               SBC HL,BC                       ; 4715 ED 42
               EX (SP),HL                      ; 4717 E3
               POP BC                          ; 4718 C1
               PUSH BC                         ; 4719 C5
               SBC HL,BC                       ; 471A ED 42
               LD B,H                          ; 471C 44
               LD C,L                          ; 471D 4D
               CALL S4724                      ; 471E CD 24 47
               POP BC                          ; 4721 C1
               JR S46E3                        ; 4722 18 BF

; ---- S4724 ---- from &470D, &471E
S4724:
               LD HL,(&5AC8)                   ; 4724 2A C8 5A
               RES 7,H                         ; 4727 CB BC
               SET 6,H                         ; 4729 CB F4
               EX DE,HL                        ; 472B EB
               BIT 6,H                         ; 472C CB 74
               CALL Z,&3FF9                    ; 472E CC F9 3F
               LD A,H                          ; 4731 7C
               EXX                             ; 4732 D9
               LD (&4CE8),SP                   ; 4733 ED 73 E8 4C
               LD HL,&FF80                     ; 4737 21 80 FF
               LD DE,&4CEA                     ; 473A 11 EA 4C
               LD BC,&0016                     ; 473D 01 16 00
               CP &FF                          ; 4740 FE FF
               JR C,S4747                      ; 4742 38 03
               LD HL,&C000                     ; 4744 21 00 C0

; ---- S4747 ---- from &4742
S4747:
               PUSH HL                         ; 4747 E5
               LD (&4763),HL                   ; 4748 22 63 47
               LD A,(&5ACF)                    ; 474B 3A CF 5A
               AND &1F                         ; 474E E6 1F
               LDIR                            ; 4750 ED B0
               POP DE                          ; 4752 D1
               PUSH DE                         ; 4753 D5
               LD HL,&4843                     ; 4754 21 43 48
               LD C,&0A                        ; 4757 0E 0A
               LDIR                            ; 4759 ED B0
               POP DE                          ; 475B D1
               LD HL,&0016                     ; 475C 21 16 00
               ADD HL,DE                       ; 475F 19
               LD SP,HL                        ; 4760 F9
               EXX                             ; 4761 D9
               CALL &0000                      ; 4762 CD 00 00
               EXX                             ; 4765 D9
               LD SP,(&4CE8)                   ; 4766 ED 7B E8 4C
               LD HL,&4CEA                     ; 476A 21 EA 4C
               LD C,&16                        ; 476D 0E 16
               LDIR                            ; 476F ED B0
               EXX                             ; 4771 D9

; ---- S4772 ---- from &4834
S4772:
               BIT 6,H                         ; 4772 CB 74
               CALL Z,&3FF9                    ; 4774 CC F9 3F
               EX DE,HL                        ; 4777 EB
               BIT 6,H                         ; 4778 CB 74
               JR NZ,S4785                     ; 477A 20 09
               LD A,(&5ACF)                    ; 477C 3A CF 5A
               DEC A                           ; 477F 3D
               LD (&5ACF),A                    ; 4780 32 CF 5A
               SET 6,H                         ; 4783 CB F4

; ---- S4785 ---- from &477A
S4785:
               SET 7,H                         ; 4785 CB FC
               LD (&5AC8),HL                   ; 4787 22 C8 5A
               RET                             ; 478A C9

; ---- S478B ---- from &4703
S478B:
               EX AF,AF'                       ; 478B 08
               BIT 6,H                         ; 478C CB 74
               JR Z,S479C                      ; 478E 28 0C
               RES 6,H                         ; 4790 CB B4
               LD A,(&5ACF)                    ; 4792 3A CF 5A
               INC A                           ; 4795 3C
               LD (&5ACF),A                    ; 4796 32 CF 5A
               LD (&5AC8),HL                   ; 4799 22 C8 5A

; ---- S479C ---- from &478E
S479C:
               ADD HL,BC                       ; 479C 09
               DEC HL                          ; 479D 2B
               LD A,H                          ; 479E 7C
               SUB &C0                         ; 479F D6 C0
               JR C,S47B5                      ; 47A1 38 12
               LD H,A                          ; 47A3 67
               INC HL                          ; 47A4 23
               PUSH HL                         ; 47A5 E5
               LD H,B                          ; 47A6 60
               LD L,C                          ; 47A7 69
               POP BC                          ; 47A8 C1
               PUSH BC                         ; 47A9 C5
               SBC HL,BC                       ; 47AA ED 42
               LD B,H                          ; 47AC 44
               LD C,L                          ; 47AD 4D
               CALL S47B5                      ; 47AE CD B5 47
               POP BC                          ; 47B1 C1
               JP S46E3                        ; 47B2 C3 E3 46

; ---- S47B5 ---- from &47A1, &47AE
S47B5:
               LD HL,(&5AC8)                   ; 47B5 2A C8 5A
               RES 7,H                         ; 47B8 CB BC
               SET 6,H                         ; 47BA CB F4
               LD A,D                          ; 47BC 7A
               EX DE,HL                        ; 47BD EB
               BIT 6,H                         ; 47BE CB 74
               CALL NZ,&3FF2                   ; 47C0 C4 F2 3F
               EXX                             ; 47C3 D9
               LD (&4CE8),SP                   ; 47C4 ED 73 E8 4C
               LD HL,&BF80                     ; 47C8 21 80 BF
               LD DE,&4CEA                     ; 47CB 11 EA 4C
               LD BC,&000C                     ; 47CE 01 0C 00
               CP &9E                          ; 47D1 FE 9E
               LD A,(&5ACF)                    ; 47D3 3A CF 5A
               DEC A                           ; 47D6 3D
               JR C,S47F3                      ; 47D7 38 1A
               LD HL,&8000                     ; 47D9 21 00 80
               AND &1F                         ; 47DC E6 1F
               LDIR                            ; 47DE ED B0
               LD HL,&47ED                     ; 47E0 21 ED 47
               LD (&800A),HL                   ; 47E3 22 0A 80
               EXX                             ; 47E6 D9
               LD SP,&8008                     ; 47E7 31 08 80
               JP &0000                        ; 47EA C3 00 00
               DEFB &D9,&11,&00,&80,&18,&15                                     ; 47ED Y.....

; ---- S47F3 ---- from &47D7
S47F3:
               AND &1F                         ; 47F3 E6 1F
               LDIR                            ; 47F5 ED B0
               LD HL,&4804                     ; 47F7 21 04 48
               LD (&BF8A),HL                   ; 47FA 22 8A BF
               EXX                             ; 47FD D9
               LD SP,&BF88                     ; 47FE 31 88 BF
               JP &0000                        ; 4801 C3 00 00
               DEFB &D9,&11,&80,&BF,&ED,&7B,&E8,&4C,&21,&EA,&4C,&0E,&0C,&ED,&B0 ; 4804 Y..?m{hL!jL..m0
               DEFB &D9,&CB,&74,&C4,&F2,&3F,&CB,&7A                             ; 4813 YKtDr?Kz

; ---- S481B ---- from &4841
S481B:
               EX DE,HL                        ; 481B EB
               JR Z,S4825                      ; 481C 28 07
               LD A,(&5ACF)                    ; 481E 3A CF 5A
               INC A                           ; 4821 3C
               LD (&5ACF),A                    ; 4822 32 CF 5A

; ---- S4825 ---- from &481C
S4825:
               SET 7,H                         ; 4825 CB FC
               RES 6,H                         ; 4827 CB B4
               LD (&5AC8),HL                   ; 4829 22 C8 5A
               RET                             ; 482C C9

; ---- S482D ---- from &46EF
S482D:
               EX DE,HL                        ; 482D EB
               EX AF,AF'                       ; 482E 08
               JR C,S4837                      ; 482F 38 06
               EX AF,AF'                       ; 4831 08
               LDDR                            ; 4832 ED B8
               JP S4772                        ; 4834 C3 72 47

; ---- S4837 ---- from &482F
S4837:
               EX AF,AF'                       ; 4837 08
               LDIR                            ; 4838 ED B0

; ---- S483A ---- from &46DE
S483A:
               BIT 6,H                         ; 483A CB 74
               CALL NZ,&3FF2                   ; 483C C4 F2 3F
               BIT 6,D                         ; 483F CB 72
               JR S481B                        ; 4841 18 D8
               DEFB &D3,&FA,&CD,&92,&00,&3E,&1F,&D3,&FA,&C9                     ; 4843 SzM..>.SzI

; --------------------------------------------------------------------
; second stub, from &7BA4
; --------------------------------------------------------------------
               DEFB &2A,&67,&5A,&CD,&05,&00,&2A,&8B,&5B,&ED,&4B,&5E,&5A,&A7,&ED ; 484D *gZM..*.[mK^Z'm
               DEFB &42,&D0,&2A,&9A,&5A,&2B,&22,&65,&5A,&C9                     ; 485C BP*.Z+"eZI

EDITV_TARGET:
               LD A,(&5C71)                    ; 4866 3A 71 5C
               AND &20                         ; 4869 E6 20
               JR NZ,S4889                     ; 486B 20 1C
               POP HL                          ; 486D E1
               LD (&4AF1),HL                   ; 486E 22 F1 4A
               LD HL,(&4AF1)                   ; 4871 2A F1 4A
               POP DE                          ; 4874 D1
               DEC DE                          ; 4875 1B
               DEC DE                          ; 4876 1B
               DEC DE                          ; 4877 1B
               LD (&5A62),DE                   ; 4878 ED 53 62 5A
               CALL &0005                      ; 487C CD 05 00
               LD HL,(&5A62)                   ; 487F 2A 62 5A
               INC HL                          ; 4882 23
               INC HL                          ; 4883 23
               INC HL                          ; 4884 23
               PUSH HL                         ; 4885 E5
               RST &08                         ; 4886 CF
               DEFB &AF                                                         ; 4887 /
               RET                             ; 4888 C9

; ---- S4889 ---- from &486B
S4889:
               LD HL,(&5AA3)                   ; 4889 2A A3 5A
               RST &08                         ; 488C CF
               DEFB &B9                                                         ; 488D 9

CMDV_TARGET:
               LD HL,&7FE6                     ; 488E 21 E6 7F
               LD (&5C59),HL                   ; 4891 22 59 5C
               LD H,A                          ; 4894 67
               LD A,(&5A89)                    ; 4895 3A 89 5A
               CP &BE                          ; 4898 FE BE
               JR C,S48A0                      ; 489A 38 04
               PUSH HL                         ; 489C E5
               RST &08                         ; 489D CF
               DEFB &B8                                                         ; 489E 8
               POP HL                          ; 489F E1

; ---- S48A0 ---- from &489A
S48A0:
               LD A,(&5A92)                    ; 48A0 3A 92 5A
               AND &40                         ; 48A3 E6 40
               JR Z,S48C5                      ; 48A5 28 1E
               PUSH HL                         ; 48A7 E5
               LD HL,&C000                     ; 48A8 21 00 C0
               LD BC,(&5A94)                   ; 48AB ED 4B 94 5A
               SBC HL,BC                       ; 48AF ED 42
               LD B,H                          ; 48B1 44
               LD C,L                          ; 48B2 4D
               LD HL,(&5A85)                   ; 48B3 2A 85 5A
               LD A,(&5A84)                    ; 48B6 3A 84 5A
               OUT (&FB),A                     ; 48B9 D3 FB
               XOR A                           ; 48BB AF
               CALL &010C                      ; 48BC CD 0C 01
               LD A,(&5A96)                    ; 48BF 3A 96 5A
               OUT (&FB),A                     ; 48C2 D3 FB
               POP HL                          ; 48C4 E1

; ---- S48C5 ---- from &48A5
S48C5:
               LD A,(&5BB6)                    ; 48C5 3A B6 5B
               AND A                           ; 48C8 A7
               JR Z,S48FA                      ; 48C9 28 2F
               LD L,A                          ; 48CB 6F
               LD A,(&5C3B)                    ; 48CC 3A 3B 5C
               RLA                             ; 48CF 17
               JR NC,S48FA                     ; 48D0 30 28
               PUSH HL                         ; 48D2 E5
               BIT 1,L                         ; 48D3 CB 4D
               LD A,&00                        ; 48D5 3E 00
               LD HL,&9FB9                     ; 48D7 21 B9 9F
               CALL NZ,&5BE0                   ; 48DA C4 E0 5B
               POP HL                          ; 48DD E1
               LD A,L                          ; 48DE 7D
               AND &05                         ; 48DF E6 05
               JR Z,S48FA                      ; 48E1 28 17
               PUSH HL                         ; 48E3 E5
               LD HL,(&5AA0)                   ; 48E4 2A A0 5A
               PUSH HL                         ; 48E7 E5
               LD A,(&5A9F)                    ; 48E8 3A 9F 5A
               PUSH AF                         ; 48EB F5
               RST &08                         ; 48EC CF
               DEFB &9D                                                         ; 48ED .
               CALL &4D11                      ; 48EE CD 11 4D
               POP AF                          ; 48F1 F1
               LD (&5A9F),A                    ; 48F2 32 9F 5A
               POP HL                          ; 48F5 E1
               LD (&5AA0),HL                   ; 48F6 22 A0 5A
               POP HL                          ; 48F9 E1

; ---- S48FA ---- from &48C9, &48D0, &48E1
S48FA:
               LD A,H                          ; 48FA 7C
               CP &94                          ; 48FB FE 94
               RET C                           ; 48FD D8
               CP &AC                          ; 48FE FE AC
               JP Z,&45A2                      ; 4900 CA A2 45
               CP &AA                          ; 4903 FE AA
               JR Z,S494F                      ; 4905 28 48
               CP &AE                          ; 4907 FE AE
               JR Z,S493E                      ; 4909 28 33
               CP &C2                          ; 490B FE C2
               JR Z,S4949                      ; 490D 28 3A
               CP &C9                          ; 490F FE C9
               JR Z,S494F                      ; 4911 28 3C
               CP &D1                          ; 4913 FE D1
               JR Z,S494F                      ; 4915 28 38
               CP &E1                          ; 4917 FE E1
               JR Z,S494F                      ; 4919 28 34
               CP &A8                          ; 491B FE A8
               JR Z,S4953                      ; 491D 28 34
               CP &A9                          ; 491F FE A9
               JR Z,S4957                      ; 4921 28 34
               CP &CD                          ; 4923 FE CD
               JR Z,S495E                      ; 4925 28 37
               CP &FD                          ; 4927 FE FD
               JR Z,S495B                      ; 4929 28 30
               CP &B3                          ; 492B FE B3
               JR Z,S4963                      ; 492D 28 34
               CP &B0                          ; 492F FE B0
               JR Z,S4963                      ; 4931 28 30
               CP &98                          ; 4933 FE 98
               JR C,S494F                      ; 4935 38 18
               CP &FF                          ; 4937 FE FF
               RET NZ                          ; 4939 C0
               POP HL                          ; 493A E1
               RST &08                         ; 493B CF
               DEFB &B1                                                         ; 493C 1
               RET                             ; 493D C9

; ---- S493E ---- from &4909
S493E:
               LD HL,(&5A97)                   ; 493E 2A 97 5A
               INC HL                          ; 4941 23
               LD C,A                          ; 4942 4F
               LD A,(HL)                       ; 4943 7E
               CP &B3                          ; 4944 FE B3
               LD A,C                          ; 4946 79
               JR Z,S494F                      ; 4947 28 06

; ---- S4949 ---- from &490D
S4949:
               LD HL,(&4AF4)                   ; 4949 2A F4 4A
               INC L                           ; 494C 2C
               DEC L                           ; 494D 2D
               RET Z                           ; 494E C8

; ---- S494F ---- from &4905, &4911, &4915, &4919, &4935, &4947
S494F:
               POP HL                          ; 494F E1
               RST &08                         ; 4950 CF
               DEFB &AD                                                         ; 4951 -
               RET                             ; 4952 C9

; ---- S4953 ---- from &491D
S4953:
               POP HL                          ; 4953 E1
               RST &08                         ; 4954 CF
               DEFB &9B                                                         ; 4955 .
               RET                             ; 4956 C9

; ---- S4957 ---- from &4921
S4957:
               POP HL                          ; 4957 E1
               RST &08                         ; 4958 CF
               DEFB &9C                                                         ; 4959 .
               RET                             ; 495A C9

; ---- S495B ---- from &4929
S495B:
               POP HL                          ; 495B E1
               RST &08                         ; 495C CF
               DEFB &B7                                                         ; 495D 7

; ---- S495E ---- from &4925
S495E:
               RST &08                         ; 495E CF
               DEFB &B2                                                         ; 495F 2
               LD A,&CD                        ; 4960 3E CD
               RET                             ; 4962 C9

; ---- S4963 ---- from &492D, &4931
S4963:
               POP HL                          ; 4963 E1
               RST &08                         ; 4964 CF
               DEFB &AE                                                         ; 4965 .
               BIT 0,C                         ; 4966 CB 41
               JP NZ,&0049                     ; 4968 C2 49 00
               LD A,(&5C5C)                    ; 496B 3A 5C 5C
               LD HL,&5C9F                     ; 496E 21 9F 5C
               ADD A,L                         ; 4971 85
               LD L,A                          ; 4972 6F
               LD L,(HL)                       ; 4973 6E
               LD A,(&5600)                    ; 4974 3A 00 56
               LD H,A                          ; 4977 67
               XOR A                           ; 4978 AF

; ---- S4979 ---- from &497D
S4979:
               INC A                           ; 4979 3C
               IN A,(&F8)                      ; 497A DB F8
               SUB H                           ; 497C 94
               JR Z,S4979                      ; 497D 28 FA
               LD A,L                          ; 497F 7D
               OUT (&FC),A                     ; 4980 D3 FC
               LD A,B                          ; 4982 78
               JP &0054                        ; 4983 C3 54 00

FRAMIV_TARGET:
               LD A,(&5600)                    ; 4986 3A 00 56
               INC A                           ; 4989 3C
               JR Z,S499A                      ; 498A 28 0E
               LD A,(&5C5B)                    ; 498C 3A 5B 5C
               AND A                           ; 498F A7
               JR Z,S499A                      ; 4990 28 08
               LD HL,&5C9F                     ; 4992 21 9F 5C
               ADD A,L                         ; 4995 85
               LD L,A                          ; 4996 6F
               LD A,(HL)                       ; 4997 7E
               OUT (&FC),A                     ; 4998 D3 FC

; ---- S499A ---- from &498A, &4990
S499A:
               IN A,(&FB)                      ; 499A DB FB
               PUSH AF                         ; 499C F5
               LD D,A                          ; 499D 57
               LD A,&00                        ; 499E 3E 00
               OUT (&FB),A                     ; 49A0 D3 FB
               CALL &99A3                      ; 49A2 CD A3 99
               POP AF                          ; 49A5 F1
               OUT (&FB),A                     ; 49A6 D3 FB
               RET                             ; 49A8 C9

PATOUT_TARGET:
               LD A,(&5AB7)                    ; 49A9 3A B7 5A
               AND A                           ; 49AC A7
               JR Z,S49CB                      ; 49AD 28 1C
               POP HL                          ; 49AF E1
               POP DE                          ; 49B0 D1
               LD A,D                          ; 49B1 7A
               CP &40                          ; 49B2 FE 40
               JR NZ,S49BA                     ; 49B4 20 04
               INC D                           ; 49B6 14
               LD (&4AED),A                    ; 49B7 32 ED 4A

; ---- S49BA ---- from &49B4
S49BA:
               CP &42                          ; 49BA FE 42
               JR NZ,S49C9                     ; 49BC 20 0B
               LD A,(&4AED)                    ; 49BE 3A ED 4A
               SUB &40                         ; 49C1 D6 40
               JR NZ,S49C9                     ; 49C3 20 04
               LD (&4AED),A                    ; 49C5 32 ED 4A
               DEC D                           ; 49C8 15

; ---- S49C9 ---- from &49BC, &49C3
S49C9:
               PUSH DE                         ; 49C9 D5
               PUSH HL                         ; 49CA E5

; ---- S49CB ---- from &49AD
S49CB:
               LD A,(&5A73)                    ; 49CB 3A 73 5A
               CP &02                          ; 49CE FE 02
               JR Z,S49F4                      ; 49D0 28 22
               LD A,(&4AEE)                    ; 49D2 3A EE 4A
               AND A                           ; 49D5 A7
               JR Z,S49E4                      ; 49D6 28 0C
               EXX                             ; 49D8 D9
               LD HL,&A485                     ; 49D9 21 85 A4
               CALL S49EE                      ; 49DC CD EE 49
               DEC E                           ; 49DF 1D
               POP HL                          ; 49E0 E1
               POP AF                          ; 49E1 F1
               PUSH DE                         ; 49E2 D5
               JP (HL)                         ; 49E3 E9

; ---- S49E4 ---- from &49D6
S49E4:
               LD A,(&4AEF)                    ; 49E4 3A EF 4A
               AND A                           ; 49E7 A7
               JR Z,S49F4                      ; 49E8 28 0A
               EXX                             ; 49EA D9
               LD HL,&A4F3                     ; 49EB 21 F3 A4

; ---- S49EE ---- from &49DC
S49EE:
               LD C,A                          ; 49EE 4F
               LD A,&00                        ; 49EF 3E 00
               JP &5BE0                        ; 49F1 C3 E0 5B

; ---- S49F4 ---- from &49D0, &49E8
S49F4:
               JP &0000                        ; 49F4 C3 00 00
               DEFB &FE,&16,&28,&05,&FE,&17,&C2,&00,&00,&32,&BE,&5B,&2A,&51,&5C ; 49F7 ~.(.~.B..2>[*Q\
               DEFB &5E,&23,&56,&ED,&53,&B5,&5A,&11,&12,&4A,&18,&06,&32,&BF,&5B ; 4A06 ^#VmS5Z..J..2?[
               DEFB &11,&1F,&4A,&2A,&51,&5C,&73,&23,&72,&C9,&57,&3A,&EE,&4A,&A7 ; 4A15 ..J*Q\s#rIW:nJ'
               DEFB &28,&06,&47,&AF,&82,&10,&FD,&57,&3A,&73,&5A,&3D,&20,&1C,&3A ; 4A24 (.G/..}W:sZ= .:
               DEFB &BE,&5B,&D6,&17,&B2,&20,&14,&3A,&3C,&5C,&17,&30,&0E,&ED,&5B ; 4A33 >[V.2 .:<\.0.m[
               DEFB &B5,&5A,&CD,&18,&4A,&3E,&20,&D7,&3E,&0D,&D7,&C9,&7A,&C3,&00 ; 4A42 5ZM.J> W>.WIzC.
               DEFB &00,&00,&00,&00,&00,&3C,&3C,&3C,&00,&00,&3C,&3C,&3C,&00,&00 ; 4A51 .....<<<..<<<..
               DEFB &00,&00,&A7,&3E,&37,&D9,&3E,&FF,&C3,&00,&00,&11,&C1,&C0,&CD ; 4A60 ..'>7Y>.C...A@M
               DEFB &00,&00,&C1,&38,&02,&CF,&05,&57,&E7,&FE,&0D,&28,&04,&FE,&3A ; 4A6F ..A8.O.Wg~.(.~:
               DEFB &20,&F7,&7A,&C3,&00,&00,&21,&B6,&5B,&CB,&C6,&3E,&FF,&32,&40 ; 4A7E  wzC..!6[KF>.2@
               DEFB &5B,&2A,&A0,&5A,&3A,&9F,&5A,&D3,&FB,&36,&00,&C9,&CD,&84,&4A ; 4A8D [* Z:.ZS{6.IM.J
               DEFB &C3,&00,&00,&22,&9E,&4B,&E1,&CD,&00,&00,&2A,&9E,&4B,&C3,&00 ; 4A9C C..".KaM..*.KC.
               DEFB &00,&FE,&50,&28,&03,&FE,&4E,&C0,&E1,&CF,&B3,&D9,&C9         ; 4AAB .~P(.~N@aO3YI

RST8V_TARGET:
               PUSH AF                         ; 4AB8 F5
               CP &1D                          ; 4AB9 FE 1D
               JR Z,S4ADB                      ; 4ABB 28 1E
               RLA                             ; 4ABD 17
               JR C,S4ADB                      ; 4ABE 38 1B
               PUSH DE                         ; 4AC0 D5
               LD HL,(&4AEE)                   ; 4AC1 2A EE 4A
               LD A,H                          ; 4AC4 7C
               CP &05                          ; 4AC5 FE 05
               JR NC,S4ACE                     ; 4AC7 30 05
               LD A,L                          ; 4AC9 7D
               CP &05                          ; 4ACA FE 05
               JR C,S4ADA                      ; 4ACC 38 0C

; ---- S4ACE ---- from &4AC7
S4ACE:
               LD HL,&0000                     ; 4ACE 21 00 00
               LD (&4AEE),HL                   ; 4AD1 22 EE 4A
               LD A,(&5A40)                    ; 4AD4 3A 40 5A
               CALL &015A                      ; 4AD7 CD 5A 01

; ---- S4ADA ---- from &4ACC
S4ADA:
               POP DE                          ; 4ADA D1

; ---- S4ADB ---- from &4ABB, &4ABE
S4ADB:
               POP AF                          ; 4ADB F1
               RET                             ; 4ADC C9
               DEFB &CF,&B4,&C9,&CF,&B5,&D9,&C5,&F1,&C9,&CF,&B6,&C9,&CF,&9A,&C9 ; 4ADD O4IO5YEqIO6IO.I

               DEFS &4BA0-$   ; the gap is not part of the file

; --------------------------------------------------------------------
; the 36 bytes from &7B80
; --------------------------------------------------------------------
               DEFB &40,&18,&03,&CF,&97,&C9,&CF,&A7,&C9,&CF,&A8,&D9,&C5,&F1,&C9 ; 4BA0 @..O.IO'IO(YEqI
               DEFB &00                                                         ; 4BAF .

PRTOKV_TARGET:
               CP &F7                          ; 4BB0 FE F7
               RET C                           ; 4BB2 D8
               POP HL                          ; 4BB3 E1
               LD HL,(&5AA3)                   ; 4BB4 2A A3 5A
               RST &08                         ; 4BB7 CF
               DEFB &A9                                                         ; 4BB8 )
               RET                             ; 4BB9 C9

EVALUV_TARGET:
               CP &25                          ; 4BBA FE 25
               JR Z,S4BC1                      ; 4BBC 28 03
               CP &21                          ; 4BBE FE 21
               RET NC                          ; 4BC0 D0

; ---- S4BC1 ---- from &4BBC
S4BC1:
               POP HL                          ; 4BC1 E1
               RST &08                         ; 4BC2 CF
               DEFB &AC                                                         ; 4BC3 ,

