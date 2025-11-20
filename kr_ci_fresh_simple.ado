capture program drop kr_ci_fresh_simple
program define kr_ci_fresh_simple, rclass
    version 14
    // MF:        main effect of MF (freshness)
    // MLF:       MF × label (freshlabel)
    // MFPREF:    MF × LFprefer (freshprefer_black)
    syntax , MF(string) MLF(string) MFPREF(string) ///
             [ REPS(integer 10000) SAVing(string) ]

    tempname b V
    matrix `b' = e(b)
    matrix `V' = e(V)

    // --- 係数の位置を取得 ---
    local idx_mf      = colnumb(`b', "mean:`mf'")
    if (`idx_mf'==.)      local idx_mf      = colnumb(`b', "`mf'")
    local idx_mlf     = colnumb(`b', "mean:`mlf'")
    if (`idx_mlf'==.)     local idx_mlf     = colnumb(`b', "`mlf'")
    local idx_mfpref  = colnumb(`b', "mean:`mfpref'")
    if (`idx_mfpref'==.)  local idx_mfpref  = colnumb(`b', "`mfpref'")

    if (`idx_mf'==.) {
        di as error "kr_ci_fresh_simple: coefficient for MF (`mf') not found in e(b)."
        exit 498
    }
    if (`idx_mlf'==.) {
        di as error "kr_ci_fresh_simple: coefficient for MF x label (`mlf') not found in e(b)."
        exit 498
    }
    if (`idx_mfpref'==.) {
        di as error "kr_ci_fresh_simple: coefficient for MF x LFprefer (`mfpref') not found in e(b)."
        exit 498
    }

    // --- 点推定 ---
    // LFprefer = 0 のとき
    scalar WTP_MF_0 = `b'[1,`idx_mf'] + `b'[1,`idx_mlf']

    // LFprefer = 1 のとき
    scalar WTP_MF_1 = WTP_MF_0 + `b'[1,`idx_mfpref']

    // 差分
    scalar dWTP = WTP_MF_1 - WTP_MF_0

    di as text "== WTP for MF (freshness) =="
    di as result " WTP_MF (LFprefer=0) = " %9.3f WTP_MF_0
    di as result " WTP_MF (LFprefer=1) = " %9.3f WTP_MF_1
    di as result " Difference          = " %9.3f dWTP

    // --- Wald test ---
    di as text "== Wald test for difference =="
    quietly lincom `mfpref'
    matrix b1 = r(b)
    matrix V1 = r(V)
    scalar d1  = b1[1,1]
    scalar se1 = sqrt(V1[1,1])
    scalar z1  = d1/se1
    scalar p1  = 2*(1-normal(abs(z1)))
    di as result " Difference: est=" %9.3f d1 ///
        "  se=" %9.3f se1 "  z=" %6.3f z1 "  p=" %6.4f p1

    // --- Krinsky–Robb draws ---
    preserve
        clear
        set obs `reps'
        local k = colsof(`b')
        drawnorm b1-b`k', means(`b') cov(`V')

        gen double WTP_MF_0 = b`idx_mf' + b`idx_mlf'
        gen double WTP_MF_1 = WTP_MF_0 + b`idx_mfpref'
        gen double dWTP = WTP_MF_1 - WTP_MF_0

        centile WTP_MF_0, centile(2.5 97.5)
        scalar WTP_MF_0_l = r(c_1)
        scalar WTP_MF_0_u = r(c_2)

        centile WTP_MF_1, centile(2.5 97.5)
        scalar WTP_MF_1_l = r(c_1)
        scalar WTP_MF_1_u = r(c_2)

        centile dWTP, centile(2.5 97.5)
        scalar dWTP_l = r(c_1)
        scalar dWTP_u = r(c_2)
    restore

    di as text "== Krinsky-Robb 95% confidence intervals (`reps' draws) =="

    local w0_l : display %9.3f WTP_MF_0_l
    local w0_u : display %9.3f WTP_MF_0_u
    local w1_l : display %9.3f WTP_MF_1_l
    local w1_u : display %9.3f WTP_MF_1_u
    local dw_l : display %9.3f dWTP_l
    local dw_u : display %9.3f dWTP_u

    di as result " WTP_MF (LFprefer=0): " `w0_l' " to " `w0_u'
    di as result " WTP_MF (LFprefer=1): " `w1_l' " to " `w1_u'
    di as result " Difference:          " `dw_l' " to " `dw_u'

    // --- ファイル保存 ---
    if ("`saving'" != "") {
        tempname myfile
        file open `myfile' using "`saving'", write text append

        file write `myfile' "=== Krinsky-Robb Results (Simple) ===" _n
        file write `myfile' "Point Estimates:" _n
        file write `myfile' "WTP_MF_0 = " %9.3f (WTP_MF_0) _n
        file write `myfile' "WTP_MF_1 = " %9.3f (WTP_MF_1) _n
        file write `myfile' "dWTP = " %9.3f (dWTP) _n
        file write `myfile' "95% Confidence Intervals:" _n
        file write `myfile' "WTP_MF_0: " %9.3f (WTP_MF_0_l) " to " %9.3f (WTP_MF_0_u) _n
        file write `myfile' "WTP_MF_1: " %9.3f (WTP_MF_1_l) " to " %9.3f (WTP_MF_1_u) _n
        file write `myfile' "dWTP: " %9.3f (dWTP_l) " to " %9.3f (dWTP_u) _n
        file write `myfile' _n

        file close `myfile'
    }

    // r() に返す
    return scalar WTP_MF_0   = WTP_MF_0
    return scalar WTP_MF_1   = WTP_MF_1
    return scalar dWTP       = dWTP
    return scalar WTP_MF_0_l = WTP_MF_0_l
    return scalar WTP_MF_0_u = WTP_MF_0_u
    return scalar WTP_MF_1_l = WTP_MF_1_l
    return scalar WTP_MF_1_u = WTP_MF_1_u
    return scalar dWTP_l     = dWTP_l
    return scalar dWTP_u     = dWTP_u
end
