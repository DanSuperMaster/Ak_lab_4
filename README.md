Здесь будет язык команд, основанный на commonlisp
```
<atom> ::= <identifier> | <number> | <string>

<identifier> ::= <char> { char> }

<char> ::= <letter> | <digit> | '$' | '_' | '.'

<number> ::= <integer> | <float> 

<integer> ::= [ '-' ] <digit> { <digit> }

<float> ::= [ '-' ] <digit> { <digit> } '.' <digit> { <digit> }

<string> ::= '"' { <string_char> } '"'

<string_char> ::= <any_char_except_quote> | '""'  


<hex_digit> ::= <digit>  | 'A' | 'B' | 'C' | 'D' | 'E' | 'F'

<letter> ::= 'A' | ... | 'Z' | 'a' | ... | 'z'

<digit> ::= '0' | ... | '9'
```
