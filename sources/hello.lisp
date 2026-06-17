(DEFUN PRINT-STR (PTR)
  (WHILE (PEEK PTR)
    (PROGN
      (WRITE (PEEK PTR))
      (SETQ PTR (+ PTR 1)))))

(PRINT-STR "Hello, World!")
(WRITE 10)
