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

(DEFUN ISPAL (X)
  (PROGN
    (SETQ R 0)
    (SETQ TMP X)
    (WHILE (> TMP 0)
      (PROGN
        (SETQ R (+ (* R 10) (% TMP 10)))
        (SETQ TMP (/ TMP 10))))
    (= R X)))

(SETQ BEST 0)
(SETQ A 999)
(WHILE (> A 99)
  (PROGN
    (SETQ B 999)
    (SETQ GO 1)
    (WHILE (* GO (> B (- A 1)))
      (PROGN
        (SETQ P (* A B))
        (IF (> P BEST)
            (IF (ISPAL P)
                (SETQ BEST P)
                (PROGN))
            (SETQ GO 0))
        (SETQ B (- B 1))))
    (SETQ A (- A 1))))

(PRINT-NUM BEST)
(WRITE 10)
