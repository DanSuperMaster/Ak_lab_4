class Lexer:

    def __init__(self, text):
        self.text = text
        self.pos = 0

    def current_char(self):
        if self.pos >= len(self.text):
            return None
        return self.text[self.pos]

    def next_char(self):
        if (self.pos + 1) >= len(self.text):
            return None
        return self.text[self.pos + 1]

    def advance(self):
        self.pos += 1

    def skip_whitespace(self):
        while (self.current_char() is not None) and (self.current_char().isspace()):
            self.advance()

    def read_integer(self):
        number = ""

        while (self.current_char() is not None) and (self.current_char().isdigit()):
            number += self.current_char()
            self.advance()

        return int(number)

    def read_string(self):
        stroke = ""
        self.advance()

        while self.current_char() is not None:
            if self.current_char() == '"':
                if self.next_char() is not None and self.next_char() == '"':
                    stroke += '"'
                    self.advance()
                    self.advance()
                    continue
                else:
                    self.advance()
                    return stroke
            stroke += self.current_char()
            self.advance()

        raise Exception("Unterminated string")

    def read_identifier(self):
        result = ""

        while self.current_char() is not None:
            char = self.current_char()

            if self.is_identifier_char(char):
                result += char
                self.advance()
            else:
                break

        return result

    def is_identifier_char(self, char):
        return not char.isspace() and char not in '()"'

    def tokenize(self):
        tokens = []

        while self.current_char() is not None:

            if self.current_char().isspace():
                self.skip_whitespace()
                continue

            if self.current_char().isdigit():
                number = self.read_integer()
                tokens.append(("INTEGER", number))
                continue

            if self.current_char() == '\"':
                stroke = self.read_string()
                tokens.append(("STRING", stroke))
                continue

            if self.current_char() == '(':
                tokens.append(("LPAREN", "("))
                self.advance()
                continue

            if self.current_char() == ')':
                tokens.append(("RPAREN", ")"))
                self.advance()
                continue

            if (self.current_char() == '-'
                    and self.next_char() is not None
                    and self.next_char().isdigit()):
                self.advance()
                number = self.read_integer()
                tokens.append(("INTEGER", -number))
                continue

            if self.is_identifier_char(self.current_char()):
                ident = self.read_identifier()
                tokens.append(("IDENTIFIER", ident))
                continue

            raise Exception(f"Unexpected char: {self.current_char()}")

        return tokens


class Parser:

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        if self.pos >= len(self.tokens):
            return None

        return self.tokens[self.pos]

    def advance(self):
        self.pos += 1

    def expect(self, token_type):
        token = self.current()

        if token is None:
            raise Exception(f"Expected {token_type}, got EOF")

        if token[0] != token_type:
            raise Exception(
                f"Expected {token_type}, got {token}"
            )

        self.advance()

        return token

    def parse(self):

        expressions = []

        while self.current() is not None:
            expressions.append(self.parse_expr())

        return expressions

    def parse_expr(self):

        token = self.current()

        if token is None:
            raise Exception("Unexpected EOF")

        token_type = token[0]

        if token_type == 'LPAREN':
            return self.parse_list()

        return self.parse_atom()

    def parse_atom(self):

        token = self.current()

        if token is None:
            raise Exception("Unexpected EOF")

        token_type = token[0]
        value = token[1]

        self.advance()

        if token_type == 'INTEGER':
            return int(value)

        if token_type == 'FLOAT':
            return float(value)

        if token_type == 'STRING':
            return ['__string__', value]

        if token_type == 'IDENTIFIER':
            return value

        raise Exception(f"Unexpected token: {token}")

    def parse_list(self):

        elements = []

        self.expect('LPAREN')

        while True:

            token = self.current()

            if token is None:
                raise Exception("Unterminated list")

            if token[0] == 'RPAREN':
                break

            elements.append(self.parse_expr())

        self.expect('RPAREN')

        return elements
