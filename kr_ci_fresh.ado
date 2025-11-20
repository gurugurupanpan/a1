capture program drop kr_ci_fresh
program define kr_ci_fresh, rclass
    version 14
    // MF:        main effect of MF (freshness)
    // MLF:       MF × label         （freshlabel）
    // MLT:       MF × labelB        （freshlabelB：Tlabelの増分）
    // MFPREF:    MF × LFprefer      （freshprefer_black）
    // MLFpref:   MF × label × LFprefer        （freshlabelprefer_black）
    // MLTpref:   MF × labelB × LFprefer       （freshlabelprefer_blackB）
    syntax , MF(string) MLF(string) MLT(string) ///
             MFPREF(string) MLFpref(string) MLTpref(string) ///
             [ REPS(integer 10000) SAVing(string) ]

    tempname b V
    matrix `b' = e(b)
    matrix `V' = e(V)

    // --- 係数の位置を取得 ---
    local idx_mf      = colnumb(`b', "mean:`mf'")
    if (`idx_mf'==.)      local idx_mf      = colnumb(`b', "`mf'")
    local idx_mlf     = colnumb(`b', "mean:`mlf'")
    if (`idx_mlf'==.)     local idx_mlf     = colnumb(`b', "`mlf'")
    local idx_mlt     = colnumb(`b', "mean:`mlt'")
    if (`idx_mlt'==.)     local idx_mlt     = colnumb(`b', "`mlt'")
    local idx_mfpref  = colnumb(`b', "mean:`mfpref'")
    if (`idx_mfpref'==.)  local idx_mfpref  = colnumb(`b', "`mfpref'")
    local idx_mlfpref = colnumb(`b', "mean:`mlfpref'")
    if (`idx_mlfpref'==.) local idx_mlfpref = colnumb(`b', "`mlfpref'")
    local idx_mltpref = colnumb(`b', "mean:`mltpref'")
    if (`idx_mltpref'==.) local idx_mltpref = colnumb(`b', "`mltpref'")

    if (`idx_mf'==.) {
        di as error "kr_ci_fresh: coefficient for MF (`mf') not found in e(b)."
        exit 498
    }
    if (`idx_mlf'==.) {
        di as error "kr_ci_fresh: coefficient for MF x label (`mlf') not found in e(b)."
        exit 498
    }
    if (`idx_mlt'==.) {
        di as error "kr_ci_fresh: coefficient for MF x labelB (`mlt') not found in e(b)."
        exit 498
    }
    if (`idx_mfpref'==.) {
        di as error "kr_ci_fresh: coefficient for MF x LFprefer (`mfpref') not found in e(b)."
        exit 498
    }
    if (`idx_mlfpref'==.) {
        di as error "kr_ci_fresh: coefficient for MF x label x LFprefer (`mlfpref') not found."
        exit 498
    }
    if (`idx_mltpref'==.) {
        di as error "kr_ci_fresh: coefficient for MF x labelB x LFprefer (`mltpref') not found."
        exit 498
    }

    // --- 点推定（式(4)–(6)に対応） ---
    // WTP_MF^A : Freshness label 群 (Group A)
    // WTP_MF^B : Tasting label 群 (Group B)
    // LFprefer = 0 のとき
    scalar WTP_MF_A0 = `b'[1,`idx_mf'] + `b'[1,`idx_mlf']
    scalar WTP_MF_B0 = `b'[1,`idx_mf'] + `b'[1,`idx_mlf'] + `b'[1,`idx_mlt']
    scalar dWTP0     = WTP_MF_A0 - WTP_MF_B0        // = - b[MLT]

    // LFprefer = 1 のとき
    // それぞれに MF×LFprefer と MF×label×LFprefer, MF×labelB×LFprefer が加わる
    scalar WTP_MF_A1 = WTP_MF_A0 ///
        + `b'[1,`idx_mfpref'] + `b'[1,`idx_mlfpref']
    scalar WTP_MF_B1 = WTP_MF_B0 ///
        + `b'[1,`idx_mfpref'] + `b'[1,`idx_mlfpref'] + `b'[1,`idx_mltpref']
    scalar dWTP1     = WTP_MF_A1 - WTP_MF_B1        // = - b[MLT] - b[MLTpref]

    // 平均 (LFpreferを固定しない)
    scalar dWTP_avg  = (dWTP0 + dWTP1) / 2

    di as text "== WTP for MF from pooled Stage-2 model =="
    di as result " WTP_MF^A (LFprefer=0)      = " %9.3f WTP_MF_A0
    di as result " WTP_MF^B (LFprefer=0)      = " %9.3f WTP_MF_B0
    di as result " ΔWTP_Fresh (LFprefer=0)    = " %9.3f dWTP0
    di as result " WTP_MF^A (LFprefer=1)      = " %9.3f WTP_MF_A1
    di as result " WTP_MF^B (LFprefer=1)      = " %9.3f WTP_MF_B1
    di as result " ΔWTP_Fresh (LFprefer=1)    = " %9.3f dWTP1
    di as result " ΔWTP_Fresh (Average)       = " %9.3f dWTP_avg

    // --- Wald test （H0: ΔWTP = 0） ---
    di as text "== Wald tests for ΔWTP_Fresh =="

    // ΔWTP_Fresh(0) = - b[MLT] なので、H0 は b[MLT] = 0
    quietly lincom `mlt'
    matrix b1 = r(b)
    matrix V1 = r(V)
    scalar d1  = -b1[1,1]
    scalar se1 = sqrt(V1[1,1])
    scalar z1  = d1/se1
    scalar p1  = 2*(1-normal(abs(z1)))
    di as result " ΔWTP_Fresh (LFprefer=0): est=" %9.3f d1 ///
        "  se=" %9.3f se1 "  z=" %6.3f z1 "  p=" %6.4f p1

    // ΔWTP_Fresh(1) = - ( b[MLT] + b[MLTpref] )
    // H0 は b[MLT] + b[MLTpref] = 0
    quietly lincom `mlt' + `mltpref'
    matrix b2 = r(b)
    matrix V2 = r(V)
    scalar d2  = -b2[1,1]
    scalar se2 = sqrt(V2[1,1])
    scalar z2  = d2/se2
    scalar p2  = 2*(1-normal(abs(z2)))
    di as result " ΔWTP_Fresh (LFprefer=1): est=" %9.3f d2 ///
        "  se=" %9.3f se2 "  z=" %6.3f z2 "  p=" %6.4f p2

    // --- Krinsky–Robb draws ---
    preserve
        clear
        set obs `reps'
        local k = colsof(`b')
        drawnorm b1-b`k', means(`b') cov(`V')

        gen double WTP_MF_A0 = b`idx_mf' + b`idx_mlf'
        gen double WTP_MF_B0 = b`idx_mf' + b`idx_mlf' + b`idx_mlt'
        gen double dWTP0     = WTP_MF_A0 - WTP_MF_B0

        gen double WTP_MF_A1 = WTP_MF_A0 + b`idx_mfpref' + b`idx_mlfpref'
        gen double WTP_MF_B1 = WTP_MF_B0 + b`idx_mfpref' + b`idx_mlfpref' + b`idx_mltpref'
        gen double dWTP1     = WTP_MF_A1 - WTP_MF_B1
        gen double dWTP_avg  = (dWTP0 + dWTP1) / 2

        centile WTP_MF_A0, centile(2.5 97.5)
        scalar WTP_MF_A0_l = r(c_1)
        scalar WTP_MF_A0_u = r(c_2)

        centile WTP_MF_B0, centile(2.5 97.5)
        scalar WTP_MF_B0_l = r(c_1)
        scalar WTP_MF_B0_u = r(c_2)

        centile dWTP0, centile(2.5 97.5)
        scalar dWTP0_l = r(c_1)
        scalar dWTP0_u = r(c_2)

        centile WTP_MF_A1, centile(2.5 97.5)
        scalar WTP_MF_A1_l = r(c_1)
        scalar WTP_MF_A1_u = r(c_2)

        centile WTP_MF_B1, centile(2.5 97.5)
        scalar WTP_MF_B1_l = r(c_1)
        scalar WTP_MF_B1_u = r(c_2)

        centile dWTP1, centile(2.5 97.5)
        scalar dWTP1_l = r(c_1)
        scalar dWTP1_u = r(c_2)

        centile dWTP_avg, centile(2.5 97.5)
        scalar dWTP_avg_l = r(c_1)
        scalar dWTP_avg_u = r(c_2)
    restore

    di as text "== Krinsky–Robb 95% confidence intervals (`reps' draws) =="

    // フォーマット済みの値をローカルマクロに格納
    local A0_l : display %9.3f WTP_MF_A0_l
    local A0_u : display %9.3f WTP_MF_A0_u
    local B0_l : display %9.3f WTP_MF_B0_l
    local B0_u : display %9.3f WTP_MF_B0_u
    local d0_l : display %9.3f dWTP0_l
    local d0_u : display %9.3f dWTP0_u
    local A1_l : display %9.3f WTP_MF_A1_l
    local A1_u : display %9.3f WTP_MF_A1_u
    local B1_l : display %9.3f WTP_MF_B1_l
    local B1_u : display %9.3f WTP_MF_B1_u
    local d1_l : display %9.3f dWTP1_l
    local d1_u : display %9.3f dWTP1_u
    local davg_l : display %9.3f dWTP_avg_l
    local davg_u : display %9.3f dWTP_avg_u

    di as result " WTP_MF^A (LFprefer=0):      " `A0_l' " to " `A0_u'
    di as result " WTP_MF^B (LFprefer=0):      " `B0_l' " to " `B0_u'
    di as result " ΔWTP_Fresh (LFprefer=0):    " `d0_l' " to " `d0_u'
    di as result " WTP_MF^A (LFprefer=1):      " `A1_l' " to " `A1_u'
    di as result " WTP_MF^B (LFprefer=1):      " `B1_l' " to " `B1_u'
    di as result " ΔWTP_Fresh (LFprefer=1):    " `d1_l' " to " `d1_u'
    di as result " ΔWTP_Fresh (Average):       " `davg_l' " to " `davg_u'

    // --- テキストファイルへの保存 ---
    if ("`saving'" != "") {
        tempname myfile
        file open `myfile' using "`saving'", write text append

        file write `myfile' "=== Krinsky-Robb Results ===" _n
        file write `myfile' "Point Estimates:" _n
        file write `myfile' "WTP_MF_A0 = " %9.3f (WTP_MF_A0) _n
        file write `myfile' "WTP_MF_B0 = " %9.3f (WTP_MF_B0) _n
        file write `myfile' "dWTP0 = " %9.3f (dWTP0) _n
        file write `myfile' "WTP_MF_A1 = " %9.3f (WTP_MF_A1) _n
        file write `myfile' "WTP_MF_B1 = " %9.3f (WTP_MF_B1) _n
        file write `myfile' "dWTP1 = " %9.3f (dWTP1) _n
        file write `myfile' "dWTP_avg = " %9.3f (dWTP_avg) _n
        file write `myfile' "95% Confidence Intervals:" _n
        file write `myfile' "WTP_MF_A0: " %9.3f (WTP_MF_A0_l) " to " %9.3f (WTP_MF_A0_u) _n
        file write `myfile' "WTP_MF_B0: " %9.3f (WTP_MF_B0_l) " to " %9.3f (WTP_MF_B0_u) _n
        file write `myfile' "dWTP0: " %9.3f (dWTP0_l) " to " %9.3f (dWTP0_u) _n
        file write `myfile' "WTP_MF_A1: " %9.3f (WTP_MF_A1_l) " to " %9.3f (WTP_MF_A1_u) _n
        file write `myfile' "WTP_MF_B1: " %9.3f (WTP_MF_B1_l) " to " %9.3f (WTP_MF_B1_u) _n
        file write `myfile' "dWTP1: " %9.3f (dWTP1_l) " to " %9.3f (dWTP1_u) _n
        file write `myfile' "dWTP_avg: " %9.3f (dWTP_avg_l) " to " %9.3f (dWTP_avg_u) _n
        file write `myfile' _n

        file close `myfile'
    }

    // r() に返す
    return scalar WTP_MF_A0   = WTP_MF_A0
    return scalar WTP_MF_B0   = WTP_MF_B0
    return scalar dWTP0       = dWTP0
    return scalar WTP_MF_A1   = WTP_MF_A1
    return scalar WTP_MF_B1   = WTP_MF_B1
    return scalar dWTP1       = dWTP1
    return scalar dWTP_avg    = dWTP_avg

    return scalar WTP_MF_A0_l = WTP_MF_A0_l
    return scalar WTP_MF_A0_u = WTP_MF_A0_u
    return scalar WTP_MF_B0_l = WTP_MF_B0_l
    return scalar WTP_MF_B0_u = WTP_MF_B0_u
    return scalar dWTP0_l     = dWTP0_l
    return scalar dWTP0_u     = dWTP0_u

    return scalar WTP_MF_A1_l = WTP_MF_A1_l
    return scalar WTP_MF_A1_u = WTP_MF_A1_u
    return scalar WTP_MF_B1_l = WTP_MF_B1_l
    return scalar WTP_MF_B1_u = WTP_MF_B1_u
    return scalar dWTP1_l     = dWTP1_l
    return scalar dWTP1_u     = dWTP1_u

    return scalar dWTP_avg_l  = dWTP_avg_l
    return scalar dWTP_avg_u  = dWTP_avg_u
end
