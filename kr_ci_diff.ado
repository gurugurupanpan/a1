capture program drop kr_ci_diff
program define kr_ci_diff, rclass
    version 14
    // 2つのパラメータの差のKrinsky-Robb信頼区間を計算
    syntax , PARAM1(string) PARAM2(string) ///
             [ REPS(integer 10000) SAVing(string) Level(real 95) ]

    tempname b V
    matrix `b' = e(b)
    matrix `V' = e(V)

    // パーセンタイルを計算
    local alpha = (100 - `level') / 2
    local lower = `alpha'
    local upper = 100 - `alpha'

    // パラメータ1の位置を取得
    local idx1 = colnumb(`b', "mean:`param1'")
    if (`idx1'==.) local idx1 = colnumb(`b', "`param1'")
    if (`idx1'==.) {
        di as error "kr_ci_diff: parameter `param1' not found in e(b)"
        exit 498
    }

    // パラメータ2の位置を取得
    local idx2 = colnumb(`b', "mean:`param2'")
    if (`idx2'==.) local idx2 = colnumb(`b', "`param2'")
    if (`idx2'==.) {
        di as error "kr_ci_diff: parameter `param2' not found in e(b)"
        exit 498
    }

    // 点推定
    scalar val1 = `b'[1,`idx1']
    scalar val2 = `b'[1,`idx2']
    scalar diff = val2 - val1

    di as text "== Point Estimates =="
    di as result " `param1' = " %9.3f val1
    di as result " `param2' = " %9.3f val2
    di as result " Difference (`param2' - `param1') = " %9.3f diff

    // Wald test
    quietly lincom `param2' - `param1'
    matrix b_diff = r(b)
    matrix V_diff = r(V)
    scalar diff_se = sqrt(V_diff[1,1])
    scalar diff_z = diff / diff_se
    scalar diff_p = 2*(1-normal(abs(diff_z)))

    di as text "== Wald test for difference =="
    di as result " Difference: est=" %9.3f diff ///
        "  se=" %9.3f diff_se "  z=" %6.3f diff_z "  p=" %6.4f diff_p

    // Krinsky-Robb draws
    preserve
        clear
        set obs `reps'
        local k = colsof(`b')
        drawnorm b1-b`k', means(`b') cov(`V')

        gen double param1 = b`idx1'
        gen double param2 = b`idx2'
        gen double diff = param2 - param1

        centile param1, centile(`lower' `upper')
        scalar val1_l = r(c_1)
        scalar val1_u = r(c_2)

        centile param2, centile(`lower' `upper')
        scalar val2_l = r(c_1)
        scalar val2_u = r(c_2)

        centile diff, centile(`lower' `upper')
        scalar diff_l = r(c_1)
        scalar diff_u = r(c_2)
    restore

    di as text "== Krinsky-Robb `level'% Confidence Intervals (`reps' draws) =="

    local v1_l : display %9.3f val1_l
    local v1_u : display %9.3f val1_u
    local v2_l : display %9.3f val2_l
    local v2_u : display %9.3f val2_u
    local d_l : display %9.3f diff_l
    local d_u : display %9.3f diff_u

    di as result " `param1': " `v1_l' " to " `v1_u'
    di as result " `param2': " `v2_l' " to " `v2_u'
    di as result " Difference: " `d_l' " to " `d_u'

    // ファイル保存
    if ("`saving'" != "") {
        tempname myfile
        file open `myfile' using "`saving'", write text append

        file write `myfile' "=== Difference between `param2' and `param1' ===" _n
        file write `myfile' "Point Estimates:" _n
        file write `myfile' "`param1' = " %9.3f (val1) _n
        file write `myfile' "`param2' = " %9.3f (val2) _n
        file write `myfile' "Difference = " %9.3f (diff) _n
        file write `myfile' "`level'% Confidence Intervals:" _n
        file write `myfile' "`param1': " %9.3f (val1_l) " to " %9.3f (val1_u) _n
        file write `myfile' "`param2': " %9.3f (val2_l) " to " %9.3f (val2_u) _n
        file write `myfile' "Difference: " %9.3f (diff_l) " to " %9.3f (diff_u) _n
        file write `myfile' _n

        file close `myfile'
    }

    // r() に返す
    return scalar `param1' = val1
    return scalar `param2' = val2
    return scalar diff = diff
    return scalar diff_se = diff_se
    return scalar diff_p = diff_p

    return scalar `param1'_l = val1_l
    return scalar `param1'_u = val1_u
    return scalar `param2'_l = val2_l
    return scalar `param2'_u = val2_u
    return scalar diff_l = diff_l
    return scalar diff_u = diff_u
end
