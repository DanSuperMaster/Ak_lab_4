(DEFUN PRINT-NUM (PNN)
  (IF (= PNN 0)
      (WRITE 48)
      (PROGN
        (SETQ PND 1000000)
        (SETQ PNS 0)
        (WHILE (> PND 0)
          (PROGN
            (SETQ PNG (/ PNN PND))
            (IF (> (+ PNG PNS) 0)
                (PROGN
                  (SETQ PNS 1)
                  (WRITE (+ PNG 48))
                  (SETQ PNN (- PNN (* PNG PND))))
                (PROGN))
            (SETQ PND (/ PND 10)))))))

(DEFUN ALEN (ALP)
  (PROGN
    (SETQ ALN 0)
    (WHILE (PEEK (+ ALP ALN))
      (SETQ ALN (+ ALN 1)))
    ALN))

(DEFUN SORT (SP)
  (PROGN
    (SETQ SN (ALEN SP))
    (SETQ SLV -1)
    (SETQ SLI -1)
    (SETQ SOU 0)
    (WHILE (< SOU SN)
      (PROGN
        (SETQ SBI -1)
        (SETQ SBV 0)
        (SETQ SI 0)
        (WHILE (< SI SN)
          (PROGN
            (SETQ SVI (PEEK (+ SP SI)))
            (IF (> (+ (> SVI SLV) (* (= SVI SLV) (> SI SLI))) 0)
                (IF (> (+ (+ (= SBI -1) (< SVI SBV)) (* (= SVI SBV) (< SI SBI))) 0)
                    (PROGN
                      (SETQ SBV SVI)
                      (SETQ SBI SI))
                    (PROGN))
                (PROGN))
            (SETQ SI (+ SI 1))))
        (PRINT-NUM SBV)
        (WRITE 32)
        (SETQ SLV SBV)
        (SETQ SLI SBI)
        (SETQ SOU (+ SOU 1))))))

(SORT (LIST 5 3 8 1 3 9 2 7))
(WRITE 10)
