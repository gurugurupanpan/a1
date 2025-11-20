capture program drop kr_ci_params
program define kr_ci_params, rclass
    version 14
    // 個別パラメータのKrinsky-Robb信頼区間を計算
    syntax namelist(min=1) [, REPS(integer 10000) SAVing(string) Level(real 95)]

    tempname b V
    matrix `b' = e(b)
    matrix `V' = e(V)

    // パーセンタイルを計算
    local alpha = (100 - `level') / 2
    local lower = `alpha'
    local upper = 100 - `alpha'

    // 各パラメータの位置を取得
    local nparams : word count `namelist'
    local paramlist ""
    forvalues i = 1/`nparams' {
        local param : word `i' of `namelist'
        local idx_`i' = colnumb(`b', "mean:`param'")
        if (`idx_`i''==.) local idx_`i' = colnumb(`b', "`param'")

        if (`idx_`i''==.) {
            di as error "kr_ci_params: parameter `param' not found in e(b)"
            exit 498
        }

        // 点推定
        scalar val_`i' = `b'[1,`idx_`i'']
        local paramlist "`paramlist' `param'"
    }

    // 点推定を表示
    di as text "== Point Estimates =="
    forvalues i = 1/`nparams' {
        local param : word `i' of `namelist'
        di as result " `param' = " %9.3f val_`i'
    }

    // Krinsky-Robb draws
    preserve
        clear
        set obs `reps'
        local k = colsof(`b')
        drawnorm b1-b`k', means(`b') cov(`V')

        // 各パラメータの信頼区間を計算
        forvalues i = 1/`nparams' {
            gen double param_`i' = b`idx_`i''
            centile param_`i', centile(`lower' `upper')
            scalar val_`i'_l = r(c_1)
            scalar val_`i'_u = r(c_2)
        }
    restore

    // 信頼区間を表示
    di as text "== Krinsky-Robb `level'% Confidence Intervals (`reps' draws) =="
    forvalues i = 1/`nparams' {
        local param : word `i' of `namelist'
        local v_l : display %9.3f val_`i'_l
        local v_u : display %9.3f val_`i'_u
        di as result " `param': " `v_l' " to " `v_u'
    }

    // ファイル保存
    if ("`saving'" != "") {
        tempname myfile
        file open `myfile' using "`saving'", write text append

        file write `myfile' "=== Krinsky-Robb CI for Individual Parameters ===" _n
        file write `myfile' "Point Estimates:" _n
        forvalues i = 1/`nparams' {
            local param : word `i' of `namelist'
            file write `myfile' "`param' = " %9.3f (val_`i') _n
        }
        file write `myfile' "`level'% Confidence Intervals:" _n
        forvalues i = 1/`nparams' {
            local param : word `i' of `namelist'
            file write `myfile' "`param': " %9.3f (val_`i'_l) " to " %9.3f (val_`i'_u) _n
        }
        file write `myfile' _n

        file close `myfile'
    }

    // r() に返す
    forvalues i = 1/`nparams' {
        local param : word `i' of `namelist'
        return scalar `param' = val_`i'
        return scalar `param'_l = val_`i'_l
        return scalar `param'_u = val_`i'_u
    }
end
