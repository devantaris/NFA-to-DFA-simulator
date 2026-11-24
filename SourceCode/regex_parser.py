"""Regular Expression to NFA converter using Thompson's Construction Algorithm.

Converts infix regular expressions with operators (*, +, ?, |, ., ()) to
equivalent non-deterministic finite automata (NFA) compatible with NFAtoDFAConverter.
"""

from __future__ import annotations
import enum
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

if __package__ in (None, ""):
    _ROOT = Path(__file__).resolve().parent.parent
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    from SourceCode.models import EPSILON, is_epsilon
    from SourceCode.nfa import NFA
else:
    from .models import EPSILON, is_epsilon
    from .nfa import NFA


class RegexParseError(ValueError):
    """Raised when a regular expression string has invalid syntax or structure."""
    pass


class TokenType(enum.Enum):
    LITERAL = "LITERAL"
    EPSILON = "EPSILON"
    CONCAT = "CONCAT"
    UNION = "UNION"
    STAR = "STAR"
    PLUS = "PLUS"
    QUESTION = "QUESTION"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"


@dataclass
class Token:
    type: TokenType
    val: str
    pos: int

    def __repr__(self) -> str:
        return f"{self.type.name}({self.val})"


@dataclass
class Fragment:
    start_state: str
    accept_state: str
    states: Set[str]
    transitions: Dict[Tuple[str, str], Set[str]]
    alphabet: Set[str]


class ThompsonBuilder:
    """Constructs primitive NFA fragments and composite operations."""

    def __init__(self) -> None:
        self.counter = 0

    def new_state(self) -> str:
        s = f"s{self.counter}"
        self.counter += 1
        return s

    def literal(self, symbol: str) -> Fragment:
        s_in = self.new_state()
        s_out = self.new_state()
        return Fragment(
            start_state=s_in,
            accept_state=s_out,
            states={s_in, s_out},
            transitions={(s_in, symbol): {s_out}},
            alphabet={symbol},
        )

    def epsilon(self) -> Fragment:
        s_in = self.new_state()
        s_out = self.new_state()
        return Fragment(
            start_state=s_in,
            accept_state=s_out,
            states={s_in, s_out},
            transitions={(s_in, EPSILON): {s_out}},
            alphabet=set(),
        )

    def concat(self, f1: Fragment, f2: Fragment) -> Fragment:
        states = f1.states | f2.states
        transitions: Dict[Tuple[str, str], Set[str]] = {}
        for k, v in f1.transitions.items():
            transitions.setdefault(k, set()).update(v)
        for k, v in f2.transitions.items():
            transitions.setdefault(k, set()).update(v)
        transitions.setdefault((f1.accept_state, EPSILON), set()).add(f2.start_state)
        return Fragment(
            start_state=f1.start_state,
            accept_state=f2.accept_state,
            states=states,
            transitions=transitions,
            alphabet=f1.alphabet | f2.alphabet,
        )

    def union(self, f1: Fragment, f2: Fragment) -> Fragment:
        s_in = self.new_state()
        s_out = self.new_state()
        states = f1.states | f2.states | {s_in, s_out}
        transitions: Dict[Tuple[str, str], Set[str]] = {}
        for k, v in f1.transitions.items():
            transitions.setdefault(k, set()).update(v)
        for k, v in f2.transitions.items():
            transitions.setdefault(k, set()).update(v)
        transitions.setdefault((s_in, EPSILON), set()).update({f1.start_state, f2.start_state})
        transitions.setdefault((f1.accept_state, EPSILON), set()).add(s_out)
        transitions.setdefault((f2.accept_state, EPSILON), set()).add(s_out)
        return Fragment(
            start_state=s_in,
            accept_state=s_out,
            states=states,
            transitions=transitions,
            alphabet=f1.alphabet | f2.alphabet,
        )

    def star(self, f: Fragment) -> Fragment:
        s_in = self.new_state()
        s_out = self.new_state()
        states = f.states | {s_in, s_out}
        transitions: Dict[Tuple[str, str], Set[str]] = {}
        for k, v in f.transitions.items():
            transitions.setdefault(k, set()).update(v)
        transitions.setdefault((s_in, EPSILON), set()).update({f.start_state, s_out})
        transitions.setdefault((f.accept_state, EPSILON), set()).update({f.start_state, s_out})
        return Fragment(
            start_state=s_in,
            accept_state=s_out,
            states=states,
            transitions=transitions,
            alphabet=f.alphabet,
        )

    def plus(self, f: Fragment) -> Fragment:
        s_in = self.new_state()
        s_out = self.new_state()
        states = f.states | {s_in, s_out}
        transitions: Dict[Tuple[str, str], Set[str]] = {}
        for k, v in f.transitions.items():
            transitions.setdefault(k, set()).update(v)
        transitions.setdefault((s_in, EPSILON), set()).add(f.start_state)
        transitions.setdefault((f.accept_state, EPSILON), set()).update({f.start_state, s_out})
        return Fragment(
            start_state=s_in,
            accept_state=s_out,
            states=states,
            transitions=transitions,
            alphabet=f.alphabet,
        )

    def question(self, f: Fragment) -> Fragment:
        s_in = self.new_state()
        s_out = self.new_state()
        states = f.states | {s_in, s_out}
        transitions: Dict[Tuple[str, str], Set[str]] = {}
        for k, v in f.transitions.items():
            transitions.setdefault(k, set()).update(v)
        transitions.setdefault((s_in, EPSILON), set()).update({f.start_state, s_out})
        transitions.setdefault((f.accept_state, EPSILON), set()).add(s_out)
        return Fragment(
            start_state=s_in,
            accept_state=s_out,
            states=states,
            transitions=transitions,
            alphabet=f.alphabet,
        )


def tokenize(regex: str) -> List[Token]:
    """Tokenize regular expression string with escape sequence handling."""
    tokens: List[Token] = []
    i = 0
    n = len(regex)
    while i < n:
        c = regex[i]
        if c.isspace():
            i += 1
            continue
        if c == "\\":
            if i + 1 >= n:
                raise RegexParseError("Invalid regular expression: trailing backslash at end of input")
            tokens.append(Token(TokenType.LITERAL, regex[i + 1], i))
            i += 2
        elif c == "(":
            tokens.append(Token(TokenType.LPAREN, c, i))
            i += 1
        elif c == ")":
            tokens.append(Token(TokenType.RPAREN, c, i))
            i += 1
        elif c == "|":
            tokens.append(Token(TokenType.UNION, c, i))
            i += 1
        elif c == "*":
            tokens.append(Token(TokenType.STAR, c, i))
            i += 1
        elif c == "+":
            tokens.append(Token(TokenType.PLUS, c, i))
            i += 1
        elif c == "?":
            tokens.append(Token(TokenType.QUESTION, c, i))
            i += 1
        elif c == EPSILON:
            tokens.append(Token(TokenType.EPSILON, EPSILON, i))
            i += 1
        else:
            tokens.append(Token(TokenType.LITERAL, c, i))
            i += 1
    return tokens


def validate_tokens(tokens: List[Token]) -> None:
    """Validate lexical and structural token sequence."""
    if not tokens:
        return

    # Check leading operators
    if tokens[0].type in (TokenType.STAR, TokenType.PLUS, TokenType.QUESTION):
        raise RegexParseError(
            f"Invalid regular expression: leading repetition operator '{tokens[0].val}' at position {tokens[0].pos}"
        )
    if tokens[0].type == TokenType.UNION:
        raise RegexParseError(
            f"Invalid regular expression: leading union operator '|' at position {tokens[0].pos}"
        )

    # Check trailing operators
    if tokens[-1].type == TokenType.UNION:
        raise RegexParseError(
            f"Invalid regular expression: trailing union operator '|' at position {tokens[-1].pos}"
        )

    paren_depth = 0
    for i, tok in enumerate(tokens):
        if tok.type == TokenType.LPAREN:
            paren_depth += 1
            # Check for empty parentheses ()
            if i + 1 < len(tokens) and tokens[i + 1].type == TokenType.RPAREN:
                raise RegexParseError(
                    f"Invalid regular expression: empty parentheses '()' at position {tok.pos}"
                )
        elif tok.type == TokenType.RPAREN:
            paren_depth -= 1
            if paren_depth < 0:
                raise RegexParseError(
                    f"Invalid regular expression: unmatched ')' at position {tok.pos}"
                )
        elif tok.type in (TokenType.STAR, TokenType.PLUS, TokenType.QUESTION):
            prev = tokens[i - 1]
            if prev.type not in (TokenType.LITERAL, TokenType.EPSILON, TokenType.RPAREN):
                raise RegexParseError(
                    f"Invalid regular expression: operator '{tok.val}' has nothing to repeat at position {tok.pos}"
                )
        elif tok.type == TokenType.UNION:
            prev = tokens[i - 1]
            if prev.type in (TokenType.UNION, TokenType.LPAREN):
                raise RegexParseError(
                    f"Invalid regular expression: unexpected '|' at position {tok.pos}"
                )
            if i + 1 < len(tokens) and tokens[i + 1].type == TokenType.RPAREN:
                raise RegexParseError(
                    f"Invalid regular expression: unexpected '|' before ')' at position {tok.pos}"
                )

    if paren_depth > 0:
        raise RegexParseError("Invalid regular expression: unclosed '(' in expression")


def insert_concatenation(tokens: List[Token]) -> List[Token]:
    """Insert explicit concatenation tokens ('.') between adjacent atom tokens."""
    if not tokens:
        return []

    can_end = {
        TokenType.LITERAL,
        TokenType.EPSILON,
        TokenType.RPAREN,
        TokenType.STAR,
        TokenType.PLUS,
        TokenType.QUESTION,
    }
    can_start = {TokenType.LITERAL, TokenType.EPSILON, TokenType.LPAREN}

    result: List[Token] = []
    for i, tok in enumerate(tokens):
        result.append(tok)
        if i + 1 < len(tokens):
            next_tok = tokens[i + 1]
            if tok.type in can_end and next_tok.type in can_start:
                result.append(Token(TokenType.CONCAT, ".", tok.pos))
    return result


def infix_to_postfix(tokens: List[Token]) -> List[Token]:
    """Convert infix tokens to postfix tokens using Dijkstra's Shunting-Yard algorithm."""
    precedence = {
        TokenType.UNION: 1,
        TokenType.CONCAT: 2,
    }
    output: List[Token] = []
    op_stack: List[Token] = []

    for tok in tokens:
        if tok.type in (TokenType.LITERAL, TokenType.EPSILON):
            output.append(tok)
        elif tok.type in (TokenType.STAR, TokenType.PLUS, TokenType.QUESTION):
            output.append(tok)
        elif tok.type in (TokenType.UNION, TokenType.CONCAT):
            while (
                op_stack
                and op_stack[-1].type != TokenType.LPAREN
                and precedence.get(op_stack[-1].type, 0) >= precedence[tok.type]
            ):
                output.append(op_stack.pop())
            op_stack.append(tok)
        elif tok.type == TokenType.LPAREN:
            op_stack.append(tok)
        elif tok.type == TokenType.RPAREN:
            while op_stack and op_stack[-1].type != TokenType.LPAREN:
                output.append(op_stack.pop())
            if not op_stack:
                raise RegexParseError("Invalid regular expression: unmatched ')'")
            op_stack.pop()

    while op_stack:
        top = op_stack.pop()
        if top.type == TokenType.LPAREN:
            raise RegexParseError("Invalid regular expression: unclosed '('")
        output.append(top)

    return output


def evaluate_postfix(postfix_tokens: List[Token]) -> Fragment:
    """Evaluate postfix tokens using Thompson Fragment stack."""
    builder = ThompsonBuilder()
    if not postfix_tokens:
        return builder.epsilon()

    stack: List[Fragment] = []
    for tok in postfix_tokens:
        if tok.type == TokenType.LITERAL:
            stack.append(builder.literal(tok.val))
        elif tok.type == TokenType.EPSILON:
            stack.append(builder.epsilon())
        elif tok.type == TokenType.CONCAT:
            if len(stack) < 2:
                raise RegexParseError("Invalid regular expression: missing operands for concatenation")
            f2 = stack.pop()
            f1 = stack.pop()
            stack.append(builder.concat(f1, f2))
        elif tok.type == TokenType.UNION:
            if len(stack) < 2:
                raise RegexParseError("Invalid regular expression: missing operands for union")
            f2 = stack.pop()
            f1 = stack.pop()
            stack.append(builder.union(f1, f2))
        elif tok.type == TokenType.STAR:
            if not stack:
                raise RegexParseError("Invalid regular expression: missing operand for '*'")
            f = stack.pop()
            stack.append(builder.star(f))
        elif tok.type == TokenType.PLUS:
            if not stack:
                raise RegexParseError("Invalid regular expression: missing operand for '+'")
            f = stack.pop()
            stack.append(builder.plus(f))
        elif tok.type == TokenType.QUESTION:
            if not stack:
                raise RegexParseError("Invalid regular expression: missing operand for '?'")
            f = stack.pop()
            stack.append(builder.question(f))

    if len(stack) != 1:
        raise RegexParseError(f"Invalid regular expression: unreduced fragments (count={len(stack)})")

    return stack[0]


def canonicalize_fragment(frag: Fragment, name: str) -> NFA:
    """Relabel fragment states into clean sequential labels 'q0', 'q1', ... via BFS."""
    mapping: Dict[str, str] = {frag.start_state: "q0"}
    queue: deque[str] = deque([frag.start_state])
    order: List[str] = ["q0"]

    # Adjacency map for BFS traversal
    adj: Dict[str, Set[str]] = {}
    for (st, sym), tgts in frag.transitions.items():
        adj.setdefault(st, set()).update(tgts)

    while queue:
        curr = queue.popleft()
        for nxt in sorted(adj.get(curr, set())):
            if nxt not in mapping:
                lbl = f"q{len(mapping)}"
                mapping[nxt] = lbl
                queue.append(nxt)
                order.append(lbl)

    # Any unreachable or disconnected states
    for st in sorted(frag.states):
        if st not in mapping:
            lbl = f"q{len(mapping)}"
            mapping[st] = lbl
            order.append(lbl)

    new_states = set(order)
    new_transitions: Dict[Tuple[str, str], Set[str]] = {}
    for (st, sym), tgts in frag.transitions.items():
        new_st = mapping[st]
        new_tgts = {mapping[t] for t in tgts}
        new_transitions[(new_st, sym)] = new_tgts

    return NFA(
        states=new_states,
        alphabet=frag.alphabet,
        transitions=new_transitions,
        start_state="q0",
        final_states={mapping[frag.accept_state]},
        name=name,
    )


def parse_regex_to_nfa(regex: str, name: str = "NFA_from_regex") -> NFA:
    """Parse an infix regular expression into a standardized NFA using Thompson's construction."""
    tokens = tokenize(regex)
    validate_tokens(tokens)
    tokens_with_concat = insert_concatenation(tokens)
    postfix_tokens = infix_to_postfix(tokens_with_concat)
    fragment = evaluate_postfix(postfix_tokens)
    return canonicalize_fragment(fragment, name=name)


def regex_to_nfa(regex: str, name: str = "NFA_from_regex") -> NFA:
    """Convenience alias for parse_regex_to_nfa."""
    return parse_regex_to_nfa(regex, name=name)


def regex_to_nfa_dict(regex: str, name: str = "NFA_from_regex") -> Dict[str, Any]:
    """Parse regular expression and return JSON-serializable dictionary representation."""
    return parse_regex_to_nfa(regex, name=name).to_dict()
