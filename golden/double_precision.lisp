(SETQ E9 (* (* 1000 1000) 1000))
(SETQ E8 (* 10000 10000))

(SETQ A0 (- E9 1))
(SETQ A1 (- E9 1))
(SETQ A2 0)

(SETQ B0 2)
(SETQ B1 0)
(SETQ B2 0)

(SETQ R0 0)
(SETQ R1 0)
(SETQ R2 0)

(DEFUN ADD64 ()
  (PROGN
    (SETQ R0 (+ A0 B0))
    (SETQ R1 (+ A1 B1))
    (SETQ R2 (+ A2 B2))
    (IF (< R0 E9)
        (PROGN)
        (PROGN
          (SETQ R0 (- R0 E9))
          (SETQ R1 (+ R1 1))))
    (IF (< R1 E9)
        (PROGN)
        (PROGN
          (SETQ R1 (- R1 E9))
          (SETQ R2 (+ R2 1))))))

(DEFUN PNP (N PAD)
  (IF (= N 0)
      (IF (= PAD 1)
          (PROGN
            (WRITE 48) (WRITE 48) (WRITE 48) (WRITE 48) (WRITE 48)
            (WRITE 48) (WRITE 48) (WRITE 48) (WRITE 48))
          (WRITE 48))
      (PROGN
        (SETQ DIV E8)
        (SETQ STARTED 0)
        (WHILE (> DIV 0)
          (PROGN
            (SETQ DIGIT (/ N DIV))
            (IF (> (+ (+ DIGIT STARTED) PAD) 0)
                (PROGN
                  (SETQ STARTED 1)
                  (WRITE (+ DIGIT 48))
                  (SETQ N (- N (* DIGIT DIV))))
                (PROGN))
            (SETQ DIV (/ DIV 10)))))))

(DEFUN PRINT64 ()
  (PROGN
    (IF (> R2 0)
        (PROGN
          (PNP R2 0)
          (PNP R1 1)
          (PNP R0 1))
        (IF (> R1 0)
            (PROGN
              (PNP R1 0)
              (PNP R0 1))
            (PNP R0 0)))
    (WRITE 10)))

(ADD64)
(PRINT64)
