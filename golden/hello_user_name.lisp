(DEFUN PRINT-STR (PTR)
  (WHILE (PEEK PTR)
    (PROGN
      (WRITE (PEEK PTR))
      (SETQ PTR (+ PTR 1)))))

(PRINT-STR "What is your name?")
(WRITE 10)

(PRINT-STR "Hello, ")
(SETQ C (READ))
(WHILE (- C 10)
  (PROGN
    (WRITE C)
    (SETQ C (READ))))
(WRITE 33)
(WRITE 10)
