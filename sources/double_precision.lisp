(DEFUN PRINT-NUM (PNN)
  (IF (= PNN 0)
      (WRITE 48)
      (PROGN
        (SETQ PND (* (* 1000 1000) 1000))
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

(SETQ A0 -1)
(SETQ A1 10)
(SETQ A2 7)

(SETQ B0 5)
(SETQ B1 20)
(SETQ B2 0)

(SETQ R0 (+ A0 B0))
(SETQ R1 (+C A1 B1))
(SETQ R2 (+C A2 B2))

(PRINT-NUM R2) (WRITE 32)
(PRINT-NUM R1) (WRITE 32)
(PRINT-NUM R0) (WRITE 10)
