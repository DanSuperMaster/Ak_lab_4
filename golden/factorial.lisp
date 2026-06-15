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

(DEFUN FACT (N)
  (IF (< N 2)
      1
      (* N (FACT (- N 1)))))

(PRINT-NUM (FACT 7))
(WRITE 10)
